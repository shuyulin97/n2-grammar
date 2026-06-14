// speech.js 檔案內容

// 確保瀏覽器支援 Web Speech API
const synth = window.speechSynthesis;
let jaVoice = null;
let voicesLoaded = false;

// 載入語音清單並尋找最佳日文語音
function loadVoices() {
    if (!synth) return; // 如果不支援則直接退出
    
    const voices = synth.getVoices();
    if (voices.length > 0) {
        // 尋找策略：
        // 1. 優先找 Google 日本語 (通常品質最好)
        // 2. 退而求其次找 iOS/Mac 內建的日文語音 (如 Kyoko 或 Otoya)
        // 3. 找任何標示為 ja-JP 的語音
        jaVoice = voices.find(v => v.name.includes('Google 日本語')) || 
                  voices.find(v => v.lang === 'ja-JP' && v.localService === true) ||
                  voices.find(v => v.lang.includes('ja'));
        
        voicesLoaded = true;
        
        if (!jaVoice) {
            console.warn("找不到系統內建的日文語音套件。");
        }
    }
}

// 處理語音非同步載入
// 結合事件監聽與定時檢查，增加跨瀏覽器（特別是 Safari）的穩定性
if (synth !== undefined) {
    if (synth.onvoiceschanged !== undefined) {
        synth.onvoiceschanged = loadVoices;
    }
    // 立即嘗試載入
    loadVoices();
    
    // 針對某些不會觸發 onvoiceschanged 的瀏覽器作後備處理
    if (!voicesLoaded) {
       setTimeout(loadVoices, 500); 
    }
}

function speakSentence(text) {
    if (!synth) {
        alert("您的瀏覽器不支援語音朗讀功能。");
        return;
    }

    // 播放前先取消目前的發音
    synth.cancel();

    // 如果字串是空的，就不浪費資源執行
    if (!text || text.trim() === '') return;

    const utterance = new SpeechSynthesisUtterance(text);
    
    // 設定語言為日文
    utterance.lang = 'ja-JP';
    
    // 參數微調 (可依個人喜好調整)
    utterance.rate = 1.0;   // 語速: 0.1 到 10 (預設 1)
    utterance.pitch = 1.0;  // 音高: 0 到 2 (預設 1)
    utterance.volume = 1.0; // 音量: 0 到 1 (預設 1)
    
    // 指定日文語音
    if (jaVoice) {
        utterance.voice = jaVoice;
    } else {
        // 如果真的找不到，雖然會用預設語音唸，但至少能在開發者工具看到警告
        console.warn("目前使用系統預設語音發音，可能無法正確朗讀日文。");
    }

    synth.speak(utterance);
}