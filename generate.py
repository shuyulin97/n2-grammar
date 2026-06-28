import os
import json
import re
from openai import OpenAI
import glob

# 1. 取得環境變數
api_key = os.environ.get("LLAMA_API_KEY")
issue_title = os.environ.get("ISSUE_TITLE", "未命名文法")
issue_body = os.environ.get("ISSUE_BODY", "")

# 2. 自動計算下一個檔案序號
existing_files = glob.glob("[0-9][0-9]-*.html")
next_number = len(existing_files) + 1
formatted_number = f"{next_number:02d}"

# 3. 設定本地 LLaMA API（OpenAI SDK 格式）
client = OpenAI(
    api_key=api_key,
    base_url="https://gangway-remedy-unrobed.ngrok-free.dev/v1",
)

# 4. Prompt
prompt = f"""
你是一個專業的日文文法老師，也熟悉 HTML 排版。請根據以下文法主題，產出詳細的文法解說頁面內容。

【文法主題】
「{issue_title}」

【參考備註（若有）】
{issue_body}

---

【內容深度要求】
請比照「時雨之町（時雨日文）」的風格進行講解，每個區塊都要達到以下深度：

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

5. 【易混淆文法比較】（若有相近文法）
   - 說明此文法「不能用」的情境（搭配 ❌ 示範句），與能用的文法做對比
   - 請使用比較表格或條列式清楚呈現差異

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
- 日文例句中提及的【文法主題】「{issue_title}」的日文字：使用 <span class="grammar-highlight"> 包裝
- 【重要】當某個日文漢字「同時需要振假名 AND grammar-highlight 標示」時，巢狀順序必須是：
  <ruby> 在外層，<span class="grammar-highlight"> 在內層包住漢字本體，<rt> 放在 span 之後：
  ✅ 正確：<ruby><span class="grammar-highlight">関</span><rt>かか</rt></ruby><span class="grammar-highlight">わる</span>
  ❌ 錯誤：<span class="grammar-highlight"><ruby>挙句<rt>あげく</rt></ruby></span>
  錯誤寫法會導致振假名完全無法顯示，請務必遵守。
- 除了文法主題以外，其他需要強調的說明文字：使用 <strong> 包裝

例句排版規範：
- 只要出現日文例句，句尾「一律」加上發音按鈕：
  <button onclick="speakSentence('純日文字串，不含HTML標籤')">🔊 發音</button>
- 發音按鈕後換行，中文翻譯放在 <br> 之後，以（）包住
- 【例文】區塊的例句用 <ul><li>...</li></ul> 包裝
- 其他區塊（解說、比較）的例句依上下文直接排版，不強制加 <ul>

比較表格：
- 使用 <table class="compare-table"> 製作，欄位至少包含「文法句型」與「核心差異/使用限制」
- 表格內的日文例句也要加上發音按鈕

title 欄位：
- 只填「日文文法項目」＋中文意思，格式固定為「～文法項目」中文意思。範例：「～ばかりだ」越來越...／只等著...
- 禁止加上任何前綴（N2、N2文法、文法等），數字編號也不需要，Python 腳本會自動加上。

---

【輸出格式】
請只輸出一個合法的 JSON 物件，不要有任何說明文字、markdown 區塊或其他內容：
{{
  "romaji_slug": "只填文法核心的羅馬拼音（小寫、空格用連字號，不含數字與副檔名）",
  "title": "「～文法項目」中文意思",
  "content_html": "完整的 HTML 內容字串"
}}
"""

# 5. 呼叫本地 LLaMA API
print("⏳ 正在呼叫 LLaMA API...")
response = client.chat.completions.create(
    model="local-model",   # llama.cpp 忽略此參數，填任意字串即可
    messages=[
        {
            "role": "system",
            "content": "你是一個專業的日文文法老師與 HTML 排版專家。請嚴格按照使用者要求的 JSON 格式輸出，不要輸出任何其他內容。"
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.3,   # 低溫度讓格式輸出更穩定
)

raw_text = response.choices[0].message.content.strip()

# 6. 解析 JSON（容錯處理：移除可能包住 JSON 的 markdown 區塊）
cleaned = re.sub(r'^```(?:json)?\s*', '', raw_text)
cleaned = re.sub(r'\s*```$', '', cleaned).strip()

try:
    ai_data = json.loads(cleaned)
except json.JSONDecodeError as e:
    print(f"❌ JSON 解析失敗：{e}")
    print(f"--- AI 原始回應 ---\n{raw_text}\n---")
    raise

# 7. 在 Python 端強制組裝標題，完全不依賴 AI 的格式
raw_title = ai_data["title"].strip()

# 移除 AI 可能自行加上的各種前綴
raw_title = re.sub(r'^(N\d+\s*)?文法\d*\s*', '', raw_title)
raw_title = re.sub(r'^N\d+\s*', '', raw_title)

full_title = f"N2文法{formatted_number}{raw_title}"
ai_data["title"] = full_title

# 8. 組裝檔名與讀取 HTML 模板
new_filename = f"{formatted_number}-{ai_data['romaji_slug']}.html"

with open("template.html", "r", encoding="utf-8") as f:
    template = f.read()

template = template.replace("{{title}}", full_title)
template = template.replace("{{content_html}}", ai_data["content_html"])

with open(new_filename, "w", encoding="utf-8") as f:
    f.write(template)

print(f"✅ 已產生檔案：{new_filename}（標題：{full_title}）")

# 9. 更新 index.html
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
