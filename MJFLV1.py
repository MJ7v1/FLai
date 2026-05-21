import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import io
import random
import base64
from supabase import create_client, Client
import scipy.io.wavfile as wav

# --- 1. பின்னணிப் படத்தை அமைக்கும் பகுதி ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return ""

def set_bg_image(image_file):
    bin_str = get_base64(image_file)
    if bin_str:
        st.markdown(f'''
        <style>
        .stApp {{ background-image: url("data:image/png;base64,{bin_str}"); background-size: cover; }}
        h1, h2, h3, p, span, .stMarkdown, .stText, label {{ color: white !important; text-shadow: 2px 2px 4px #000000; }}
        [data-testid="stSidebar"] {{ background-color: rgba(0, 0, 0, 0.8) !important; }}
        </style>
        ''', unsafe_allow_html=True)

# --- 2. Setup ---
st.set_page_config(page_title="FLai V3.5 Pro", layout="wide")
set_bg_image('image2.png')

URL = "https://iryagjzdzqxqsqqhowcu.supabase.co"
KEY = "sb_publishable_eJqUvTMF80eliQTCLLVkYg_OrQiTCsG"
supabase: Client = create_client(URL, KEY)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'current' not in st.session_state: st.session_state.current = None

# --- 3. மியூசிக் லாஜிக் (முந்தைய கோடில் இருந்த அதே லாஜிக்) ---
MOOD_PROPS = {
    "😊 Happy": {"scale": [0, 2, 4, 5, 7, 9, 11], "bpm": 124, "pattern": [0, 4, 7, 12], "durations": [0.5, 0.5]},
    "😢 Sad": {"scale": [0, 2, 3, 5, 7, 8, 10], "bpm": 60, "pattern": [0, 2, 3, 5], "durations": [1.0, 2.0]},
    "😱 Horror": {"scale": [0, 1, 6, 7, 11], "bpm": 45, "pattern": [0, 1, 6], "durations": [0.5, 2.0, 4.0]},
    "🎤 RAP": {"scale": [0, 1, 3, 5, 7, 8, 10], "bpm": 90, "pattern": [0, 0, 3, 0], "durations": [0.25, 0.5]}
}
ROOTS = {"C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71}

def synthesize_audio(notes, times, durs, bpm):
    sample_rate = 44100
    if not notes: return None
    total_time = (max(times) + max(durs)) * (60/bpm)
    audio = np.zeros(int(total_time * sample_rate) + 1000)
    for n, t, d in zip(notes, times, durs):
        freq = 440.0 * (2.0 ** ((n - 69) / 12.0))
        start = int(t * (60/bpm) * sample_rate)
        end = int((t + d) * (60/bpm) * sample_rate)
        t_arr = np.linspace(0, d * (60/bpm), end - start, False)
        wave = (0.6 * np.sin(2 * np.pi * freq * t_arr) + 0.3 * np.sin(2 * np.pi * 2 * freq * t_arr))
        decay = np.exp(-3 * t_arr / (d * (60/bpm)))
        audio[start:end] += (wave * decay) * 0.3
    audio = (audio * 32767 / np.max(np.abs(audio))).astype(np.int16)
    byte_io = io.BytesIO()
    wav.write(byte_io, sample_rate, audio)
    return byte_io.getvalue()

def plot_piano_roll(m_notes, m_times, m_durs):
    if not m_notes: return None
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor('black')
    ax.set_facecolor('#1a1a1a')
    ax.set_ylim(min(m_notes)-2, max(m_notes)+2)
    for n, t, d in zip(m_notes, m_times, m_durs):
        ax.add_patch(plt.Rectangle((t, n-0.4), d, 0.8, color='#1DB954'))
    ax.tick_params(colors='white')
    return fig

# --- 4. SIDEBAR (Fixed Login Logic) ---
with st.sidebar:
    if not st.session_state.logged_in:
        st.header("Login 🔑")
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        
        if st.button("Login"):
            try:
                # Supabase Login
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                if res.user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.rerun() # லாகின் ஆனவுடன் ரீரன் செய்யும்
            except Exception:
                st.error("Invalid credentials!")
    else:
        st.write(f"User: **{st.session_state.user_email}**")
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.logged_in = False
            st.rerun()
        
        # Settings
        root_choice = st.selectbox("Root", list(ROOTS.keys()))
        mood_choice = st.selectbox("Mood", list(MOOD_PROPS.keys()))
        beats_choice = st.slider("Beats", 4, 32, 16)

# --- 5. MAIN APP ---
if st.session_state.logged_in:
    st.title("FLai: AI Music Assistant 🎹☁️")
    if st.button("Generate & Save"):
        # (Generate logic remains same as before)
        props = MOOD_PROPS[mood_choice]
        scale = [ROOTS[root_choice] + i for i in props['scale']]
        m_notes, m_times, m_durs = [], [], []
        curr = 0
        while curr < beats_choice:
            note = random.choice(scale)
            dur = random.choice(props['durations'])
            if curr + dur > beats_choice: dur = beats_choice - curr
            m_notes.append(note); m_times.append(curr); m_durs.append(dur); curr += dur
        
        st.session_state.current = {'notes': m_notes, 'times': m_times, 'durs': m_durs, 'bpm': props['bpm'], 'audio': synthesize_audio(m_notes, m_times, m_durs, props['bpm'])}
    
    if st.session_state.current:
        fig = plot_piano_roll(st.session_state.current['notes'], st.session_state.current['times'], st.session_state.current['durs'])
        st.pyplot(fig)
        st.audio(st.session_state.current['audio'], format='audio/wav')
else:
    st.title("Welcome to FLai 🎹")
