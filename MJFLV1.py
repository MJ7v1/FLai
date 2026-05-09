import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import io
import random
from supabase import create_client, Client

# --- 1. சுபபேஸ் இணைப்பு (Supabase Setup) ---
URL = "https://iryagjzdzqxqsqqhowcu.supabase.co"
KEY = "sb_publishable_eJqUvTMF80eliQTCLLVkYg_OrQiTCsG"
supabase: Client = create_client(URL, KEY)

# --- 2. தொடக்க நிலை அமைப்புகள் (Initialization) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'current' not in st.session_state:
    st.session_state.current = None

# --- 3. UI Helper Functions ---

def synthesize_audio(notes, times, durs, bpm):
    sample_rate = 44100
    total_time = (max(times) + max(durs)) * (60/bpm)
    audio = np.zeros(int(total_time * sample_rate))
    for n, t, d in zip(notes, times, durs):
        freq = 440.0 * (2.0 ** ((n - 69) / 12.0))
        start = int(t * (60/bpm) * sample_rate)
        end = int((t + d) * (60/bpm) * sample_rate)
        t_arr = np.linspace(0, d * (60/bpm), end - start, False)
        wave = 0.6 * np.sin(2 * np.pi * freq * t_arr)
        decay = np.exp(-3 * t_arr / (d * (60/bpm)))
        envelope = np.sin(np.pi * np.linspace(0, 1, end-start)) * decay
        audio[start:end] += (wave * envelope) * 0.3
    max_val = np.max(np.abs(audio))
    audio = (audio * 32767 / (max_val if max_val > 0 else 1)).astype(np.int16)
    byte_io = io.BytesIO()
    import scipy.io.wavfile as wav
    wav.write(byte_io, sample_rate, audio)
    return byte_io.getvalue()

def plot_piano_roll(m_notes, m_times, m_durs):
    fig, ax = plt.subplots(figsize=(10, 4))
    for n, t, d in zip(m_notes, m_times, m_durs):
        ax.add_patch(plt.Rectangle((t, n-0.4), d, 0.8, color='#1DB954'))
    ax.set_ylim(min(m_notes)-2, max(m_notes)+2)
    ax.set_xlim(0, max(m_times)+2)
    return fig

# --- 4. AUTH UI (Sidebar Login) ---

with st.sidebar:
    if not st.session_state.logged_in:
        st.header("Login / Sign Up 🔑")
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        
        c1, c2 = st.columns(2)
        if c1.button("Login"):
          try:
              res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
              st.session_state.logged_in = True
              st.session_state.user_email = email
              st.rerun()
           except Exception as e:
              st.error(f"Error: {e}") # இங்கே பிழை என்னவென்று நேரடியாகக் காட்டும்

                
        if c2.button("Sign Up"):
            try:
                supabase.auth.sign_up({"email": email, "password": pw})
                st.success("Account Created! Now Login.")
            except:
                st.error("Sign Up Failed!")
    else:
        st.write(f"Logged in as: **{st.session_state.user_email}**")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
# --- 5. MAIN APP LOGIC ---

if st.session_state.logged_in:
    st.title("FLai: AI Music Dashboard 🎹")
    
    # மெலடி உருவாக்கும் கோட்கள் இங்கே தொடரும்...
    mood = st.selectbox("Select Mood", ["😊 Happy", "😢 Sad", "😱 Horror"])
    
    if st.button("Generate Music"):
        # உங்கள் பழைய Melody Generation Logic-ஐ இங்கே இடலாம்
        st.success("Music Generated!")
else:
    st.info("இடதுபுறம் உள்ள Sidebar-இல் Login செய்து உங்கள் இசையை உருவாக்கத் தொடங்குங்கள்! 🎵")
