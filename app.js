const setupScreen = document.getElementById('setup-screen');
const callScreen = document.getElementById('call-screen');
const startCallBtn = document.getElementById('start-call-btn');
const micBtn = document.getElementById('mic-btn');
const chatLog = document.getElementById('chat-log');
const statusText = document.getElementById('status-text');
const avatar = document.getElementById('ai-avatar');

let apiKey = '';
let vocabData = []; // Array von Objekten: { word: "hola", count: 0 }
let conversationHistory = [];

// Speech Recognition Setup (Web Speech API)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = 'es-ES'; // Spanisch
recognition.interimResults = false;
recognition.maxAlternatives = 1;

// Speech Synthesis Setup
const synth = window.speechSynthesis;

// Event Listeners
startCallBtn.addEventListener('click', initiateCall);
micBtn.addEventListener('click', toggleListening);

function initiateCall() {
    apiKey = document.getElementById('api-key').value.trim();
    const vocabInput = document.getElementById('vocab-list').value;
    
    if (!apiKey) {
        alert("Bitte gib einen API-Key ein.");
        return;
    }
    
    // Vokabeln verarbeiten und in Objekte umwandeln (für Zählfunktion)
    const words = vocabInput.split(',').map(w => w.trim().toLowerCase()).filter(w => w);
    if (words.length === 0) {
        alert("Bitte füge mindestens ein paar Vokabeln hinzu.");
        return;
    }
    
    vocabData = words.map(word => ({ word: word, count: 0 }));

    // UI wechseln
    setupScreen.classList.remove('active');
    callScreen.classList.active = 'active'; // Fix für Sichtbarkeit
    callScreen.style.display = 'block';
    
    // Konversation starten (KI spricht zuerst)
    triggerAIFirstMessage();
}

async function triggerAIFirstMessage() {
    statusText.innerText = "KI denkt nach...";
    const initialPrompt = "Wir starten jetzt. Bitte stelle mir sofort die erste kurze Frage auf Spanisch.";
    await fetchGrokResponse(initialPrompt, true);
}

// --- KI & API Logik ---
async function fetchGrokResponse(userMessage, isInitial = false) {
    statusText.innerText = "KI tippt/denkt...";
    
    if (!isInitial) {
        addMessageToLog("Du", userMessage, 'user');
        conversationHistory.push({ role: "user", content: userMessage });
    }

    // Finde Wörter, die am wenigsten benutzt wurden
    vocabData.sort((a, b) => a.count - b.count);
    const leastUsedWords = vocabData.slice(0, 3).map(v => v.word).join(", ");
    const allWords = vocabData.map(v => v.word).join(", ");

    const systemPrompt = `Du bist ein spanischer Sprachpartner in einem Video-Call. 
    REGEL 1: Du darfst AUSSCHLIESSLICH die folgenden Wörter in deinen Antworten verwenden: [${allWords}]. Verwende keine anderen Wörter.
    REGEL 2: Deine Aufgabe ist es, mich zum Sprechen zu bringen, indem du mir kurze Fragen stellst.
    REGEL 3: Versuche systematisch diese spezifischen Wörter in deiner jetzigen Antwort einzubauen, da sie noch nicht oft genutzt wurden: [${leastUsedWords}].`;

    const messages = [
        { role: "system", content: systemPrompt },
        ...conversationHistory
    ];

    if (isInitial) {
        messages.push({ role: "user", content: "Starte die Konversation jetzt mit einer Frage aus den erlaubten Wörtern." });
    }

    try {
        const response = await fetch("https://api.x.ai/v1/chat/completions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: "grok-beta", // Nutze das korrekte Grok-Modell
                messages: messages,
                temperature: 0.3 // Niedrig halten, damit sich die KI an die Wörter hält
            })
        });

        const data = await response.json();
        const aiMessage = data.choices[0].message.content;
        
        // Tracking der genutzten Wörter aktualisieren
        updateVocabCounts(aiMessage);
        
        conversationHistory.push({ role: "assistant", content: aiMessage });
        addMessageToLog("Grok", aiMessage, 'ai');
        speakText(aiMessage);

    } catch (error) {
        console.error(error);
        statusText.innerText = "Fehler bei der API-Verbindung.";
    }
}

function updateVocabCounts(text) {
    const cleanText = text.toLowerCase().replace(/[^\w\sáéíóúüñ]/g, '');
    const wordsUsed = cleanText.split(/\s+/);
    
    wordsUsed.forEach(word => {
        const vocabItem = vocabData.find(v => v.word === word);
        if (vocabItem) vocabItem.count++;
    });
}

// --- Audio Input / Output ---
function toggleListening() {
    statusText.innerText = "Hört zu...";
    micBtn.classList.add('listening');
    micBtn.innerText = "🛑 Aufnahme stoppen";
    recognition.start();
}

recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    micBtn.classList.remove('listening');
    micBtn.innerText = "🎙️ Sprechen";
    fetchGrokResponse(transcript); // Sendet das Gesprochene direkt an die KI
};

recognition.onerror = (event) => {
    console.error(event.error);
    statusText.innerText = "Mikrofon Fehler.";
    micBtn.classList.remove('listening');
    micBtn.innerText = "🎙️ Sprechen";
};

function speakText(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-ES'; // Spanische Stimme
    
    utterance.onstart = () => {
        avatar.classList.add('speaking');
        statusText.innerText = "KI spricht...";
    };
    
    utterance.onend = () => {
        avatar.classList.remove('speaking');
        statusText.innerText = "Verbunden";
    };
    
    synth.speak(utterance);
}

// --- UI Helper ---
function addMessageToLog(sender, text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('msg', type);
    msgDiv.innerHTML = `<strong>${sender}:</strong> ${text}`;
    chatLog.appendChild(msgDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
}
