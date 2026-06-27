import os
import json
import re
import google.generativeai as genai
import glob

# 1. 取得環境變數
api_key = os.environ.get("GEMINI_API_KEY")
issue_title = os.environ.get("ISSUE_TITLE", "未命名文法")
issue_body = os.environ.get("ISSUE_BODY", "")

# 2. 自動計算下一個檔案序號
existing_files = glob.glob("[0-9][0-9]-*.html")
next_number = len(existing_files) + 1
formatted_number = f"{next_number:02d}"

# 3. 設定 Gemini API
genai.configure(api_key=api_key)
model = genai.GenerativeModel(
    'gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
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
- 該文法的核心語法部分：使用 <span class="grammar-highlight"> 包裝
-【重要】當某個日文漢字「同時需要振假名 AND grammar-highlight 橘色標示」時，巢狀順序必須是：
     <ruby> 在外層，<span class="grammar-highlight"> 在內層包住漢字本體，<rt> 放在 span 之後：
     ✅ 正確：<ruby><span class="grammar-highlight">関</span><rt>かか</rt></ruby><span class="grammar-highlight">わる</span>
     ❌ 錯誤：<span class="grammar-highlight"><ruby>挙句<rt>あげく</rt></ruby></span>
     錯誤寫法會導致振假名完全無法顯示，請務必遵守。
- 需要強調的說明文字：使用 <strong> 包裝

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

【輸出的 JSON 結構】
{{
  "romaji_slug": "romaji",  // 只需要提供該文法核心的羅馬拼音，不需要數字和副檔名
  "title": "「～文法項目」中文意思",  // 只填文法項目與中文意思，禁止加任何前綴
  "content_html": "..."
}}
"""

# 5. 呼叫 AI 並解析 JSON
response = model.generate_content(prompt)
ai_data = json.loads(response.text)

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
