import os
import json
import google.generativeai as genai
import glob

# 1. 取得環境變數
api_key = os.environ.get("GEMINI_API_KEY")
issue_title = os.environ.get("ISSUE_TITLE", "未命名文法")
issue_body = os.environ.get("ISSUE_BODY", "")

# 2. 自動計算下一個檔案序號
# 尋找目前目錄下所有開頭為數字的 html 檔案
existing_files = glob.glob("[0-9][0-9]-*.html")
next_number = len(existing_files) + 1
formatted_number = f"{next_number:02d}"

# 3. 設定 Gemini API (強制設定為 JSON 輸出)
genai.configure(api_key=api_key)
model = genai.GenerativeModel(
    'gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

# 4. 更新 Prompt (移除原本要求它算數字的指令，改要求 slug)
prompt = f"""
你是一個專業的日文文法老師與網頁工程師。請根據以下文法主題，整理出結構化的文法解說。

【內容生成規則】
1. 講解 N2 文法主題：「{issue_title}」
2. 請比照「時雨之町（時雨日文）：https://www.sigure.tw/learn-japanese/grammar/n3/」網站的風格進行深入淺出的講解。
3. 「接續」的部分，請嚴格以「學校文法（國文法）」來做說明。
4. 參考備註：{issue_body}

【HTML 排版與格式化規則】
1. 請產出完整的 HTML 內容放入 `content_html` 欄位。
2. 標題層級規範：
   - 使用 <h3> 標記主段落（如：<h3>【意味】</h3>、<h3>【易混淆文法比較】</h3>）。
   - 若有兩種以上意思，請分開標示（如：<h3>【意味1】</h3>、<h3>【意味2】</h3>）。
   - 使用 <h4> 標記次段落（如：<h4>【解說】</h4>、<h4>【接續】</h4>、<h4>【例文】</h4>）。
   - 請在【解說】、【接續】、【例文】等 <h4> 次段落之間，以及不同的 <h3> 主段落之間，都加上 <hr> 作為分隔線。
3. 樣式規範：
   - 針對日文例文中的「日文漢字」：使用 <ruby> 與 <rt> 標籤標註振假名發音
   - 重要禁止事項：不需要對中文解說中的「一般繁體中文字」使用 <ruby> 與 <rt> 標籤
   - 該文法的核心部分必須使用 <span class="grammar-highlight"> 包裝。
4. 例句規範：
   - 無論是在【例文】區塊，還是在【解說】、【易混淆文法比較】等任何其他區塊中，只要出現「日文句子/例句」，其句尾都「必須」加上按鈕 HTML：<button onclick="speakSentence('純日文字串')">🔊 發音</button>。
   - 括號內的「純日文字串」請務必移除 ruby 標籤。
   - 日文句子的中文翻譯請放在 <br> 之後。
   - 若是專屬於【例文】區塊的例句，請額外包裝在 <ul> 與 <li> 標籤中；若是其他區塊的句子則依據上下文排版即可。
5. 若有易混淆文法，請使用 <table class="compare-table"> 製作比較表格，表格內的日文例句也必須加上發音按鈕。
6. 原標題請務必加上中文意思。例如：「N2文法07「～はもちろん / ～はもとより」不用說...、當然...」。

【輸出的 JSON 結構】
{{
  "romaji_slug": "romaji",  // 只需要提供該文法核心的羅馬拼音，不需要數字和副檔名
  "title": "N2文法{formatted_number}「～」標題＋中文意思",
  "content_html": "..."
}}
"""

# 5. 呼叫 AI 並解析 JSON
response = model.generate_content(prompt)
ai_data = json.loads(response.text) # 因為有 response_mime_type，可以直接 load

# 6. 組裝檔名與讀取 HTML 模板
new_filename = f"{formatted_number}-{ai_data['romaji_slug']}.html"

with open("template.html", "r", encoding="utf-8") as f:
    template = f.read()

template = template.replace("{{title}}", ai_data["title"])
template = template.replace("{{content_html}}", ai_data["content_html"])

# 儲存為新的 HTML 檔案
with open(new_filename, "w", encoding="utf-8") as f:
    f.write(template)

# 7. 更新 index.html 的目錄 (透過註解錨點精準替換)
with open("index.html", "r", encoding="utf-8") as f:
    index_content = f.read()

# 使用字串拼接避開網頁介面吃字的問題
anchor = "<" + "!-- NEW_LINKS_HERE --" + ">"

# 將新連結與錨點組合在一起
new_link_html = f'<li><a href="{new_filename}" target="_blank">{ai_data["title"]}</a></li>\n        {anchor}'

# 精準尋找錨點並替換
index_content = index_content.replace(anchor, new_link_html)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(index_content)


print(f"成功生成檔案：{new_filename}")
