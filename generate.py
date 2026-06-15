import os
import json
import re
import google.generativeai as genai

# 1. 取得環境變數
api_key = os.environ.get("GEMINI_API_KEY")
issue_title = os.environ.get("ISSUE_TITLE", "未命名文法")
issue_body = os.environ.get("ISSUE_BODY", "")

# 2. 設定 Gemini API
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 設計 Prompt，強制要求 JSON 輸出與 HTML 格式
prompt = f"""
你是一個專業的日文文法老師與網頁工程師。請根據以下文法主題，整理出結構化的文法解說，並嚴格以 JSON 格式回傳，不要包含 markdown 標籤如 ```json。

【內容生成規則】
1. 講解 N2 文法主題：「{issue_title}」
2. 請比照「時雨之町（時雨日文）」網站的風格與架構進行深入淺出的講解。
3. 「接續」的部分，請嚴格以「學校文法（國文法）」來做說明。
4. 使用者提供的草稿或備註（若有）：{issue_body}

【HTML 排版與格式化規則】
1. 請產出完整的 HTML 內容放入 `content_html` 欄位。
2. 標題層級規範：
   - 使用 <h3> 標記主段落（如：<h3>【意味】</h3>、<h3>【易混淆文法比較】</h3>）。
   - 若有兩種以上意思，請分開標示（如：<h3>【意味1】</h3>、<h3>【意味2】</h3>）。
   - 使用 <h4> 標記次段落（如：<h4>【解說】</h4>、<h4>【接續】</h4>、<h4>【例文】</h4>）。
   - 請在【解說】、【接續】、【例文】等 <h4> 次段落之間，以及不同的 <h3> 主段落之間，都加上 <hr> 作為分隔線。
3. 樣式規範：
   - 所有的日文漢字必須使用 <ruby> 與 <rt> 標籤標示讀音。
   - 該文法的核心部分必須使用 <span class="grammar-highlight"> 包裝。
4. 例句規範：
   - 例句必須包裝在 <ul> 與 <li> 標籤中。
   - 在每個日文例句的句尾，必須加上按鈕 HTML：<button onclick="speakSentence('純日文字串')">🔊 發音</button>。括號內的字串請務必移除 ruby 標籤。
   - 例句的中文翻譯請放在 <br> 之後。
5. 若有易混淆文法，請使用 <table class="compare-table"> 製作比較表格。
6. filename 欄位請生成一個適合的英文檔名，格式為「數字-羅馬拼音.html」，請接續現有進度命名。
7. title 欄位請務必將原標題加上中文意思。例如：「N2文法07「～はもちろん / ～はもとより」不用說...、當然...」。

【輸出的 JSON 結構】
{{
  "filename": "07-romaji.html",
  "title": "N2文法07「～」標題",
  "content_html": "<h3>【意味】</h3>\n<p><strong>中文意思</strong></p>\n<hr>\n<h4>【解說】</h4>\n<p>解說內容</p>\n<hr>\n<h4>【接續】</h4>\n<ul><li>接續方式</li></ul>\n<hr>\n<h4>【例文】</h4>\n<ul><li><ruby>日文<rt>にほんご</rt></ruby>例句<button onclick=\"speakSentence('日文例句')\">🔊 發音</button><br>（中文翻譯）</li></ul>\n<hr>\n<h3>【易混淆文法比較】</h3>\n<p>比較內容</p>"
}}
"""

# 4. 呼叫 AI
response = model.generate_content(prompt)
response_text = response.text.strip()

# 移除可能的 markdown 標記以確保 json 解析成功
if response_text.startswith("```json"):
    response_text = response_text[7:]
if response_text.endswith("```"):
    response_text = response_text[:-3]

# 5. 讀取並替換 HTML 模板
ai_data = json.loads(response_text)
new_filename = ai_data["filename"]

with open("template.html", "r", encoding="utf-8") as f:
    template = f.read()

template = template.replace("{{title}}", ai_data["title"])
template = template.replace("{{content_html}}", ai_data["content_html"])

# 儲存為新的 HTML 檔案
with open(new_filename, "w", encoding="utf-8") as f:
    f.write(template)

# 6. 更新 index.html 的目錄
with open("index.html", "r", encoding="utf-8") as f:
    index_content = f.read()

new_link = f'<li><a href="{new_filename}" target="_blank">{ai_data["title"]}</a></li>\n    </ul>'
index_content = re.sub(r'</ul>', new_link, index_content)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(index_content)

print(f"成功生成檔案：{new_filename}")
