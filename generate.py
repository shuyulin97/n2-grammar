import os
import json
import re
import time
from google import genai
from google.genai import types
import glob
from json_repair import repair_json

# 1. 取得環境變數
api_key = os.environ.get("GEMINI_API_KEY")
issue_title = os.environ.get("ISSUE_TITLE", "未命名文法")
issue_body = os.environ.get("ISSUE_BODY", "")

# 2. 自動計算下一個檔案序號
#    改為直接掃描所有 html 檔名開頭的數字，取「最大值 + 1」。
#    （原本用 glob.glob("[0-9][0-9]-*.html") 只認得剛好兩位數的檔名，
#      一旦編號進入三位數（100 以上）就抓不到，導致編號卡住重複；
#      用「檔案數量」推算下一號也很脆弱，只要中途刪過檔案或編號不連續就會算錯，
#      因此改用「掃描現有最大編號」的方式，較為穩健。）
existing_numbers = []
for fname in glob.glob("*.html"):
    match = re.match(r'^(\d+)-', os.path.basename(fname))
    if match:
        existing_numbers.append(int(match.group(1)))

next_number = (max(existing_numbers) + 1) if existing_numbers else 1
formatted_number = f"{next_number:02d}"

# 3. 設定 Gemini API（新版統一 SDK：google-genai）
client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-pro"

# 4. Prompt
prompt = f"""
你是一個專業的日文文法老師，也熟悉 HTML 排版。請根據以下文法主題，產出詳細的文法解說頁面內容。

【文法主題】
「{issue_title}」

【參考備註（若有）】
{issue_body}

---

【內容深度要求】
請比照「時雨之町（時雨日文）」的風格以繁體中文進行講解，每個區塊都要達到以下深度：

1. 【意味】
   - 說明核心意思
   - 特別說明語氣傾向：是否主要用於正面/負面/中性情境？有無情感色彩？

2. 【解說】
   - 用「學校文法（國文法）」角度解析詞性來源（例如：「あげく 本身是形式名詞，因此前方修飾語必須用連體修飾語」）
   - 動詞變化的部分，也以「學校文法（國文法）」角度說明（例如：未然形、連用形、連體形、終止形...）
   - 說明此文法的使用限制或注意事項（例如：後句不能接意志、命令、否定的情境）

3. 【接續】
   - 動詞接法與名詞接法「分開條列」，並說明每種接法的原理
   - 若有特殊音便或助詞需補充，請在條列項目下方加上說明

4. 【例文】
   - 至少 3 句，涵蓋不同使用情境
   - 如有兩種意思，每種意思各自給例文區塊

5. 【易混淆文法比較】（若有相近文法請提出，若無可略過）
   - 說明此文法「不能用」的情境（搭配 ❌ 示範句），與能用的文法做對比
   - 請使用比較表格或條列式清楚呈現差異

---

【極重要】JSON 安全規則（違反會導致整份輸出無法解析，請務必遵守）：
- 整個回應必須是合法 JSON，因此 content_html 這個字串「絕對不可以出現雙引號 " 」。
- 所有 HTML 屬性一律使用單引號：
  ✅ 正確：<span class='grammar-highlight'>...</span>、<table class='compare-table'>
  ❌ 錯誤：<span class="grammar-highlight">...</span>（雙引號會破壞 JSON 格式，導致解析失敗）
- 發音按鈕請用單引號包住整個 onclick 屬性，句子本身則用反引號（`）包住，不要用單引號或雙引號：
  ✅ 正確：<button onclick='speakSentence(`純日文字串，不含HTML標籤`)'>🔊 發音</button>
  ❌ 錯誤：<button onclick="speakSentence('...')">🔊 發音</button>
- 換行沒有限制，正常依區塊分行即可，不需要刻意擠成一行，JSON 格式會自動處理必要的換行跳脫。

---

【HTML 排版規則】

標題層級：
- <h3> 標記主段落（如：<h3>【意味】</h3>、<h3>【易混淆文法比較：A VS B】</h3>）
- 若有兩種以上意思，分開標示（<h3>【意味1】</h3>、<h3>【意味2】</h3>）
- <h4> 標記次段落（<h4>【解說】</h4>、<h4>【接續】</h4>、<h4>【例文】</h4>）
- 每個 <h3> 與 <h4> 之前，加上 <hr> 作為分隔線

樣式規範：
- 日文例句中的漢字：使用 <ruby>漢字<rt>讀音</rt></ruby> 標註振假名
- 禁止對繁體中文字使用 <ruby> 標籤
- 日文例句中提及的【文法主題】「{issue_title}」的日文字：使用 <span class='grammar-highlight'> 包裝。
-【重要】當某個日文漢字「同時需要振假名 AND <span class='grammar-highlight'>標示」時，巢狀順序必須是：
     <ruby> 在外層，<span class='grammar-highlight'> 在內層包住漢字本體，<rt> 放在 span 之後：
     ✅ 正確：<ruby><span class='grammar-highlight'>関</span><rt>かか</rt></ruby><span class='grammar-highlight'>わる</span>
     ❌ 錯誤：<span class='grammar-highlight'><ruby>挙句<rt>あげく</rt></ruby></span>
     錯誤寫法會導致振假名完全無法顯示，請務必遵守。
- 除了文法主題以外，其他需要強調的說明文字：使用 <strong> 包裝

例句排版規範：
- 只要出現日文例句，句尾「一律」加上發音按鈕：
  <button onclick='speakSentence(`純日文字串，不含HTML標籤`)'>🔊 發音</button>
- 發音按鈕後換行，中文翻譯放在 <br> 之後，以（）包住
- 【例文】區塊的例句用 <ul><li>...</li></ul> 包裝
- 其他區塊（解說、比較）的例句依上下文直接排版，不強制加 <ul>

比較表格：
- 使用 <table class='compare-table'> 製作，欄位至少包含「文法句型」與「核心差異/使用限制」
- 表格內的日文例句也要加上發音按鈕

title 欄位：
- 只填「日文文法項目」＋中文意思，格式固定為「～文法項目」中文意思。範例：「～ばかりだ」越來越...／只等著...
- 禁止加上任何前綴（N2、N2文法、文法等），數字編號也不需要，Python 腳本會自動加上。

---

【輸出的 JSON 結構】
{{
  "romaji_slug": "romaji",  // 只需要提供該文法核心的羅馬拼音，不需要數字和副檔名
  "title": "「～文法項目」中文意思",  // 只填文法項目與中文意思，禁止加任何前綴
  "content_html": "..."  // 記得：內部絕對不可出現雙引號，屬性一律用單引號
}}
"""

# 重試相關設定
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3


def strip_code_fence(text: str) -> str:
    """移除 AI 可能誤加的 ```json 或 ``` 標記（保險用）。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```(json)?', '', text).strip()
        text = re.sub(r'```$', '', text).strip()
    return text


def generate_ai_data(prompt_text: str) -> dict:
    """
    呼叫 Gemini API 產生內容。
    若 JSON 解析失敗，會先嘗試用 json_repair 修復；
    修復也失敗的話，最多重新呼叫 API MAX_RETRIES 次。
    """
    last_error = None
    raw_text = ""

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"⏳ 正在呼叫 Gemini 2.5 Pro API...（第 {attempt}/{MAX_RETRIES} 次嘗試）")

        # 0) API 呼叫本身也可能失敗（例如 503 過載、429 限流、暫時性網路錯誤），
        #    這裡必須單獨接住，否則例外會直接往外拋，完全跳過後面的重試邏輯。
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            print(f"❌ 第 {attempt} 次 API 呼叫失敗：{e}")
            last_error = e
            if attempt < MAX_RETRIES:
                wait_time = RETRY_DELAY_SECONDS * attempt  # 遞增等待：3s → 6s → 9s
                print(f"🔁 伺服器可能暫時過載，{wait_time} 秒後重試...")
                time.sleep(wait_time)
                continue  # 跳過本輪剩餘步驟，重新呼叫 API
            else:
                break  # 已達最大重試次數，跳出迴圈統一報錯

        raw_text = strip_code_fence(response.text)
        print(f"✅ API 回應完成，長度：{len(raw_text)} 字元")

        # 1) 先嘗試直接解析
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"⚠️ 第 {attempt} 次直接解析失敗：{e}")
            last_error = e

        # 2) 直接解析失敗時，用 json_repair 嘗試修復
        #    （常見可修復的問題：漏轉義的引號、多餘/缺少逗號、未閉合括號等）
        try:
            repaired = repair_json(raw_text)
            data = json.loads(repaired)
            print("✅ 使用 json_repair 修復成功，繼續執行")
            return data
        except Exception as e:
            print(f"❌ json_repair 也無法修復：{e}")
            last_error = e

        # 3) 兩種方式都失敗，且還有重試次數，就重新呼叫 API 產生新內容
        if attempt < MAX_RETRIES:
            print(f"🔁 {RETRY_DELAY_SECONDS} 秒後重新產生內容...")
            time.sleep(RETRY_DELAY_SECONDS)

    # 全部嘗試都失敗，印出原始回應方便除錯，並中止流程
    if raw_text:
        print("--- AI 原始回應（前 800 字）---")
        print(raw_text[:800])
    else:
        print("--- 每次嘗試皆在 API 呼叫階段就失敗，沒有取得任何回應內容 ---")
    raise RuntimeError(f"經過 {MAX_RETRIES} 次嘗試仍無法取得有效 JSON，最後錯誤：{last_error}")


def format_html(html: str) -> str:
    """
    在 content_html 的關鍵區塊標籤前後補上換行，讓輸出的 HTML 原始碼容易閱讀。

    這一步是在 JSON 已經成功解析、拿到「純文字字串」之後才做的後製，
    純粹是字串處理，不會經過任何 JSON 編碼/解碼，因此完全不會有破壞 JSON
    格式的風險——不管 AI 這次自己有沒有換行、換得漂不漂亮，最後產出的
    檔案格式都會是一致、可讀的。
    """
    # 這些標籤本身獨立成一行（前後都換行）
    standalone_tags = ['<hr>']
    for tag in standalone_tags:
        html = html.replace(tag, f'\n{tag}\n')

    # 這些標籤「前面」換行，讓區塊的開頭標籤獨立起始一行
    start_tags = ['<h3', '<h4', '<table', '<ul>']
    for tag in start_tags:
        html = html.replace(tag, f'\n{tag}')

    # 這些標籤「後面」換行，讓區塊結尾後另起一行
    end_tags = ['</h3>', '</h4>', '</p>', '</li>', '</ul>', '</table>']
    for tag in end_tags:
        html = html.replace(tag, f'{tag}\n')

    # 清掉因為替換而產生的多餘空白行，並移除行首行尾多餘空白
    lines = [line.strip() for line in html.split('\n')]
    lines = [line for line in lines if line]  # 移除空行
    return '\n'.join(lines)


# 5. 呼叫 AI 並解析 JSON（含自動重試與修復）
ai_data = generate_ai_data(prompt)

# 5-1. 自動排版，確保輸出的 HTML 原始碼可讀（不依賴 AI 是否配合換行）
ai_data["content_html"] = format_html(ai_data["content_html"])

# 6. 在 Python 端強制加上編號前綴，不依賴 AI
#    這樣就算 AI 沒有在 title 加編號，這裡也會統一補上
raw_title = ai_data["title"].strip()

# 移除 AI 可能自行加上的各種前綴，例如：
#   「N2文法07」、「N2 文法07」、「N2」、「文法07」 等
raw_title = re.sub(r'^(N\d+\s*)?文法\d*\s*', '', raw_title)  # 移除「N2文法07」「文法07」
raw_title = re.sub(r'^N\d+\s*',              '', raw_title)  # 移除殘留的「N2」

full_title = f"N2文法{formatted_number}{raw_title}"
ai_data["title"] = full_title


# 7. 組裝檔名與讀取 HTML 模板
new_filename = f"{formatted_number}-{ai_data['romaji_slug']}.html"

with open("template.html", "r", encoding="utf-8") as f:
    template = f.read()

# template.html 中的佔位符：{{title}} 和 {{content_html}}
template = template.replace("{{title}}", full_title)
template = template.replace("{{content_html}}", ai_data["content_html"])

# 儲存新的 HTML 檔案
with open(new_filename, "w", encoding="utf-8") as f:
    f.write(template)

print(f"✅ 已產生檔案：{new_filename}（標題：{full_title}）")

# 8. 更新 index.html（透過錨點精準插入）
with open("index.html", "r", encoding="utf-8") as f:
    index_content = f.read()

if f'href="{new_filename}"' in index_content:
    print(f"⚠️  index.html 已有 {new_filename} 的連結，略過更新。")
else:
    new_link_html = (
        f'<li><a href="{new_filename}" target="_blank">{full_title}</a></li>\n'
        f'        <!-- NEW_LINKS_HERE -->'
    )
    if '<!-- NEW_LINKS_HERE -->' in index_content:
        index_content = index_content.replace('<!-- NEW_LINKS_HERE -->', new_link_html)
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(index_content)
        print(f"✅ 已將連結加入 index.html")
    else:
        print("⚠️  index.html 找不到 <!-- NEW_LINKS_HERE --> 錨點，請手動加入連結。")
