import streamlit as st
import requests
from gtts import gTTS
import io
import base64
import speech_recognition as sr
import re

# Seiten-Setup
st.set_page_config(page_title="Spanisch Übung", page_icon="🇪🇸", layout="centered")

# --- 1. SECRETS LADEN ---
try:
    API_KEY = st.secrets["XAI_API_KEY"]
except KeyError:
    st.error("🚨 Bitte füge 'XAI_API_KEY' in deine `.streamlit/secrets.toml` ein.")
    st.stop()

# --- 2. SESSION STATE INITIALISIEREN ---
if "history" not in st.session_state:
    st.session_state.history = []
if "vocab_data" not in st.session_state:
    st.session_state.vocab_data = []
if "call_started" not in st.session_state:
    st.session_state.call_started = False
if "latest_audio_b64" not in st.session_state:
    st.session_state.latest_audio_b64 = None

# --- 3. HILFSFUNKTIONEN ---

def get_grok_response(system_prompt, user_message_content=None):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(st.session_state.history)
    
    if user_message_content:
        messages.append({"role": "user", "content": user_message_content})
        
    data = {
        "model": "grok-beta", # Oder das aktuellste Grok-Modell
        "messages": messages,
        "temperature": 0.3
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        st.error(f"API Fehler: {response.status_code} - {response.text}")
        return "Hubo un error de conexión."

def text_to_speech_autoplay(text, lang='es'):
    """Generiert Audio und speichert es als Base64 für Autoplay."""
    tts = gTTS(text, lang=lang)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    b64 = base64.b64encode(fp.getvalue()).decode()
    st.session_state.latest_audio_b64 = b64

def transcribe_audio(audio_bytes):
    """Wandelt das aufgenommene Audio in Text um."""
    recognizer = sr.Recognizer()
    # Streamlit gibt Bytes zurück, SpeechRecognition braucht ein AudioFile
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)
        try:
            # Nutzt die kostenlose Google Spracherkennung im Hintergrund
            text = recognizer.recognize_google(audio_data, language="es-ES")
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            st.warning("Spracherkennungs-Service nicht erreichbar.")
            return None

def update_vocab_counts(text):
    """Zählt, welche Wörter die KI benutzt hat."""
    clean_text = re.sub(r'[^\w\sáéíóúüñ]', '', text.lower())
    words_used = clean_text.split()
    
    for vocab in st.session_state.vocab_data:
        if vocab["word"] in words_used:
            vocab["count"] += 1

# --- 4. UI UND LOGIK ---

st.title("🤖🇪🇸 Spanisch Video-Call Simulator")

# SETUP BEREICH (Wird ausgeblendet, sobald der Anruf startet)
if not st.session_state.call_started:
    st.write("### Vorbereitung")
    vocab_input = st.text_area("Vokabeln einfügen (kommagetrennt):", 
                               placeholder="hola, bien, gato, perro, yo, tu, comer...")
    
    if st.button("📞 Anruf starten", use_container_width=True):
        words = [w.strip().lower() for w in vocab_input.split(',') if w.strip()]
        if not words:
            st.warning("Bitte gib mindestens eine Vokabel ein.")
        else:
            # Vokabel-Tracking initialisieren
            st.session_state.vocab_data = [{"word": w, "count": 0} for w in words]
            st.session_state.call_started = True
            
            # Erste Nachricht von KI triggern
            all_words = ", ".join(words)
            sys_prompt = f"Du bist ein spanischer Sprachpartner. Du darfst AUSSCHLIESSLICH diese Wörter verwenden: [{all_words}]. Keine anderen. Stelle mir jetzt sofort eine erste kurze Frage auf Spanisch aus diesen Wörtern."
            
            with st.spinner("KI startet die Konversation..."):
                ai_reply = get_grok_response(sys_prompt, "Starte das Gespräch.")
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                update_vocab_counts(ai_reply)
                text_to_speech_autoplay(ai_reply)
            
            st.rerun()

# CALL BEREICH
if st.session_state.call_started:
    # 1. Avatar und Audio-Autoplay anzeigen
    st.markdown("<h1 style='text-align: center; font-size: 80px;'>🤖</h1>", unsafe_allow_html=True)
    
    if st.session_state.latest_audio_b64:
        # Autoplay des generierten KI-Audios
        audio_html = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{st.session_state.latest_audio_b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(audio_html, unsafe_allow_html=True)
        # B64 leeren, damit es bei Reruns nicht nochmal abspielt
        st.session_state.latest_audio_b64 = None 

    # 2. Chat-Verlauf anzeigen
    st.write("---")
    for msg in st.session_state.history:
        if msg["role"] == "user":
            st.markdown(f"**🗣️ Du:** {msg['content']}")
        elif msg["role"] == "assistant":
            st.markdown(f"**🤖 Grok:** {msg['content']}")

    # 3. Audio-Aufnahme Widget (Streamlit Native)
    st.write("---")
    st.write("### Deine Antwort")
    audio_value = st.audio_input("Sprich hier auf Spanisch rein:")

    if audio_value:
        with st.spinner("Verarbeite deine Sprache..."):
            # Audio in Text umwandeln
            user_text = transcribe_audio(audio_value.getvalue())
            
            if user_text:
                st.session_state.history.append({"role": "user", "content": user_text})
                
                # Wenig genutzte Wörter finden
                sorted_vocab = sorted(st.session_state.vocab_data, key=lambda x: x["count"])
                least_used = ", ".join([v["word"] for v in sorted_vocab[:3]])
                all_words = ", ".join([v["word"] for v in st.session_state.vocab_data])
                
                # System Prompt für diese Runde
                system_prompt = f"""Du bist ein spanischer Sprachpartner. 
                REGEL 1: Du darfst AUSSCHLIESSLICH diese Wörter verwenden: [{all_words}]. 
                REGEL 2: Stelle mir kurze Fragen, um mich zum Sprechen zu bringen.
                REGEL 3: Versuche diese noch ungenutzten Wörter einzubauen: [{least_used}]."""
                
                # KI Antwort holen
                ai_reply = get_grok_response(system_prompt)
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                update_vocab_counts(ai_reply)
                
                # Audio generieren
                text_to_speech_autoplay(ai_reply)
                
                # Seite neu laden, um den neuen Chat und das Audio anzuzeigen
                st.rerun()
            else:
                st.error("Ich konnte dich leider nicht verstehen. Bitte versuche es nochmal.")
    
    # 4. Optional: Text-Fallback falls Mikrofon nicht geht
    with st.expander("Oder Text eingeben (Fallback)"):
        text_input = st.chat_input("Eingabe...")
        if text_input:
            st.session_state.history.append({"role": "user", "content": text_input})
            # Gleiche Logik wie oben beim Audio...
            sorted_vocab = sorted(st.session_state.vocab_data, key=lambda x: x["count"])
            least_used = ", ".join([v["word"] for v in sorted_vocab[:3]])
            all_words = ", ".join([v["word"] for v in st.session_state.vocab_data])
            
            system_prompt = f"Nutze NUR diese Wörter: [{all_words}]. Baue ein: [{least_used}]."
            ai_reply = get_grok_response(system_prompt)
            st.session_state.history.append({"role": "assistant", "content": ai_reply})
            update_vocab_counts(ai_reply)
            text_to_speech_autoplay(ai_reply)
            st.rerun()
