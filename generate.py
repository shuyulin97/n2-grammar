import os
import json
import re
from openai import OpenAI
import glob

# 1. 取得環境變數
api_key    = os.environ.get("LLAMA_API_KEY")
issue_title = os.environ.get("ISSUE_TITLE", "未命名文法")
issue_body  = os.environ.get("ISSUE_BODY", "")

# 2. 自動計算下一個檔案序號
existing_files = glob.glob("[0-9][0-9]-*.html")
next_number    = len(existing_files) + 1
formatted_number = f"{next_number:02d}"

# 3. 設定本地 LLaMA/Gemma API（OpenAI SDK 格式）
client = OpenAI(
    api_key=api_key,
    base_url="https://gangway-remedy-unrobed.ngrok-free.dev/v1",
)

# ---------------------------------------------------------------
# 4. System prompt：只放「角色定義 + 輸出格式規則」，不放 HTML 範例
#    目的：讓模型清楚知道輸出結構，減少 prompt token 數
# ---------------------------------------------------------------
system_prompt = """你是一個專業的日文文法老師，同時熟悉 HTML 排版。

你的任務是針對指定的 N2 日文文法主題，產出一份教學解說頁面。

【輸出規則】
1. 只輸出一個合法的 JSON 物件，不要有任何說明文字或 markdown。
2. JSON 結構如下：
{
  "romaji_slug": "文法核心的羅馬拼音（小寫、空格用連字號）",
  "title": "「日文文法項目」中文意思（禁止加 N2、文法等前綴）",
  "content_html": "完整 HTML 字串"
}

【content_html 的 HTML 規則】
- h3 用於主段落標題（意味、接續說明、易混淆比較），h4 用於次段落（解說、接續、例文）
- 每個 h3/h4 之前加 hr 分隔線
- 日文漢字加振假名：ruby 包漢字，rt 放讀音
- 文法核心詞用 span class="grammar-highlight" 標示
- 漢字同時需要振假名和 highlight 時：ruby 在外，span 在內包漢字，rt 在 span 後
- 每句日文例句後加發音按鈕：button onclick="speakSentence('純日文')"，按鈕標籤為「🔊 發音」
- 例文區塊用 ul/li 包裝，中文翻譯放在 br 後用（）包住
- 易混淆文法用 table class="compare-table" 製作比較表
- 禁止對繁體中文使用 ruby 標籤"""

# ---------------------------------------------------------------
# 5. User prompt：只放「文法主題 + 內容要求」，不重複 HTML 規則
# ---------------------------------------------------------------
user_prompt = f"""請為以下 N2 文法主題，參照時雨日文網站（https://www.sigure.tw/learn-japanese/grammar/n3/）產出教學頁面：

文法主題：「{issue_title}」
補充備註：{issue_body if issue_body else "（無）"}

內容請包含：
1. 【意味】核心意思、語氣傾向（正面/負面/中性）
2. 【解說】學校文法（國文法）角度的詞性解析、使用限制
3. 【接續】動詞與名詞各自的接法，分開條列並說明原理
4. 【例文】至少 3 句，涵蓋不同情境
5. 【易混淆文法比較】若有相近文法，說明差異並給出 ❌ 錯誤示範"""

# ---------------------------------------------------------------
# 6. 呼叫 API，設定 max_tokens 避免無限生成
# ---------------------------------------------------------------
print("⏳ 正在呼叫 API...")
response = client.chat.completions.create(
    model="local-model",   # llama.cpp / gemma.cpp 忽略此欄位
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ],
    temperature=0.3,
    max_tokens=6000,   # 約可產出 3~4 頁 HTML，超過就強制截斷
)

raw_text = response.choices[0].message.content.strip()
print(f"✅ API 回應完成，長度：{len(raw_text)} 字元")

# 7. 解析 JSON（移除模型可能包住的 markdown 區塊）
cleaned = re.sub(r'^```(?:json)?\s*', '', raw_text)
cleaned = re.sub(r'\s*```$', '',       cleaned).strip()

try:
    ai_data = json.loads(cleaned)
except json.JSONDecodeError as e:
    print(f"❌ JSON 解析失敗：{e}")
    print(f"--- AI 原始回應（前 500 字）---\n{raw_text[:500]}\n---")
    raise

# 8. Python 端強制組裝標題（不信任 AI 的格式）
raw_title = ai_data["title"].strip()
raw_title = re.sub(r'^(N\d+\s*)?文法\d*\s*', '', raw_title)
raw_title = re.sub(r'^N\d+\s*',              '', raw_title)
full_title = f"N2文法{formatted_number}{raw_title}"
ai_data["title"] = full_title

# 9. 組裝檔名、套用 template、存檔
new_filename = f"{formatted_number}-{ai_data['romaji_slug']}.html"

with open("template.html", "r", encoding="utf-8") as f:
    template = f.read()

template = template.replace("{{title}}",        full_title)
template = template.replace("{{content_html}}", ai_data["content_html"])

with open(new_filename, "w", encoding="utf-8") as f:
    f.write(template)

print(f"✅ 已產生檔案：{new_filename}（標題：{full_title}）")

# 10. 更新 index.html
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
