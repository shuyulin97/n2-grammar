// speech.js 檔案內容
let jaVoice = null;

// 載入語音清單並尋找日文語音
function loadVoices() {
    const voices = window.speechSynthesis.getVoices();
    
    // 優先尋找 Google 日本語，若無則尋找任何 ja-JP 的語音
    jaVoice = voices.find(voice => voice.name === 'Google 日本語') || 
              voices.find(voice => voice.lang === 'ja-JP' || voice.lang === 'ja_JP');
}

// 處理瀏覽器非同步載入語音的問題
window.speechSynthesis.onvoiceschanged = loadVoices;
// 立即呼叫一次以防語音已經載入完畢
loadVoices();

function speakSentence(text) {
    // 播放前先取消目前的發音，避免連續點擊造成聲音堆疊延遲
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ja-JP';
    
    // 語速調整，比較接近自然的講話速度
    utterance.rate = 1;
    
    // 如果有成功抓取到日文語音，就指定該語音
    if (jaVoice) {
        utterance.voice = jaVoice;
    }

    window.speechSynthesis.speak(utterance);
}