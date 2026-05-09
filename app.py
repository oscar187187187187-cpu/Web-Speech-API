import streamlit as st
import requests
from gtts import gTTS
import io
import base64
import speech_recognition as sr
import re

# --- EINSTELLUNGEN ---
st.set_page_config(page_title="Spanisch Trainer", page_icon="🇪🇸")

# API-Key aus den Streamlit Secrets laden
try:
    API_KEY = st.secrets["XAI_API_KEY"]
except KeyError:
    st.error("🚨 Bitte trage deinen API-Key in den Streamlit Secrets ein (Name: XAI_API_KEY).")
    st.stop()

# --- SPEICHER FÜR DEN ANRUF ---
if "history" not in st.session_state:
    st.session_state.history = []
if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = []
if "call_started" not in st.session_state:
    st.session_state.call_started = False
if "audio_to_play" not in st.session_state:
    st.session_state.audio_to_play = None

# --- FUNKTIONEN ---
def get_ai_response(system_prompt, user_text=None):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(st.session_state.history)
    
    if user_text:
        messages.append({"role": "user", "content": user_text})
        
    data = {
        "model": "grok-beta",
        "messages": messages,
        "temperature": 0.2 # Sehr niedrig, damit sie streng bei deinen Wörtern bleibt
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return "Lo siento, hubo un error."

def text_to_speech(text):
    tts = gTTS(text, lang='es')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    b64 = base64.b64encode(fp.getvalue()).decode()
    st.session_state.audio_to_play = b64

def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data, language="es-ES")
        except:
            return None

# --- APP LAYOUT ---
st.title("🇪🇸 Spanisch Video-Call")

# 1. START-BILDSCHIRM
if not st.session_state.call_started:
    st.write("Füge hier deine Wörter ein (kommagetrennt oder mit Leerzeichen):")
    vocab_input = st.text_area("Deine 519 Wörter:", height=150)
    
    if st.button("📞 Anruf starten", use_container_width=True):
        # Wörter saubermachen und speichern
        words = [w.strip().lower() for w in re.split(r'[,\s]+', vocab_input) if w.strip()]
        
        if len(words) < 10:
            st.warning("Bitte gib ein paar mehr Wörter ein, damit wir starten können.")
        else:
            st.session_state.vocab_list = words
            st.session_state.call_started = True
            
            # Erste Nachricht generieren
            all_words_str = ", ".join(words)
            sys_prompt = f"Du bist ein spanischer Sprachpartner. WICHTIGSTE REGEL: Du darfst für deine Antworten AUSSCHLIESSLICH Wörter aus dieser Liste verwenden: [{all_words_str}]. Keine anderen Wörter! Stelle mir jetzt die erste kurze Frage."
            
            with st.spinner("KI ruft an..."):
                ai_reply = get_ai_response(sys_prompt, "Start")
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                text_to_speech(ai_reply)
            st.rerun()

# 2. ANRUF-BILDSCHIRM
if st.session_state.call_started:
    # Avatar
    st.markdown("<h1 style='text-align: center; font-size: 100px;'>🤖</h1>", unsafe_allow_html=True)
    
    # KI Audio abspielen
    if st.session_state.audio_to_play:
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{st.session_state.audio_to_play}" type="audio/mp3"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)
        st.session_state.audio_to_play = None 
        
    st.write("---")
    
    # Chat-Verlauf (Transkript)
    for msg in st.session_state.history:
        if msg["role"] == "user":
            st.markdown(f"**Du:** {msg['content']}")
        else:
            st.markdown(f"**KI:** {msg['content']}")
            
    st.write("---")
    
    # Mikrofon-Eingabe
    st.write("**Deine Antwort:**")
    audio_value = st.audio_input("Sprich hier auf Spanisch:")
    
    if audio_value:
        with st.spinner("Übersetze deine Sprache..."):
            user_text = transcribe_audio(audio_value.getvalue())
            
            if user_text:
                st.session_state.history.append({"role": "user", "content": user_text})
                
                # KI antwortet streng mit deinen Wörtern
                all_words_str = ", ".join(st.session_state.vocab_list)
                sys_prompt = f"Du bist ein spanischer Sprachpartner. REGEL: Du darfst AUSSCHLIESSLICH diese Wörter verwenden: [{all_words_str}]. Keine anderen. Reagiere auf das, was der User sagt, und stelle eine neue kurze Frage."
                
                ai_reply = get_ai_response(sys_prompt)
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                text_to_speech(ai_reply)
                
                st.rerun()
            else:
                st.error("Ich konnte dich nicht verstehen. Bitte sprich nochmal.")
