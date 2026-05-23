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
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover; /* படத்தை திரையின் அளவிற்குப் பொருத்த */
            background-attachment: fixed;
            background-position: center;
        }}
        h1, h2, h3, p, span, .stMarkdown, .stText, label {{
            color: white !important;
            text-shadow: 2px 2px 4px #000000; /* எழுத்துக்கள் தெளிவாகத் தெரிய நிழல் */
        }}
        [data-testid="stSidebar"] {{
            background-color: rgba(0, 0, 0, 0.8) !important; /* Sidebar மங்கலான கருப்பு */
        }}
        </style>
        ''', unsafe_allow_html=True)

# --- 2. தொடக்க நிலை அமைப்புகள் ---
st.set_page_config(page_title="FLai V3.5 Pro", layout="wide")
# பின்னணிப் படம் 'assets' ஃபோல்டரில் இருப்பதாகக் கொள்வோம்
set_bg_image('assets/image2.png')

# Supabase இணைப்பு விவரங்கள் (மாற்ற வேண்டாம்)
URL = "https://iryagjzdzqxqsqqhowcu.supabase.co"
KEY = "sb_publishable_eJqUvTMF80eliQTCLLVkYg_OrQiTCsG"
supabase: Client = create_client(URL, KEY)

# Session StateInitialization
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'current' not in st.session_state: st.session_state.current = None
if 'history_list' not in st.session_state: st.session_state.history_list = []

# --- 3. மியூசிக் லாஜிக் ---
MOOD_PROPS = {
    "😊 Happy": {"scale": [0, 2, 4, 5, 7, 9, 11], "bpm": 124, "durations": [0.5, 1.0]},
    "😢 Sad": {"scale": [0, 2, 3, 5, 7, 8, 10], "bpm": 60, "durations": [1.0, 2.0]},
    "😱 Horror": {"scale": [0, 1, 6, 7, 11], "bpm": 45, "durations": [1.0, 2.0, 4.0]},
    "🎤 RAP": {"scale": [0, 1, 3, 5, 7, 8, 10], "bpm": 90, "durations": [0.25, 0.5]}
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
        # Piano-like wave form with harmonics
        wave = (0.6 * np.sin(2 * np.pi * freq * t_arr) + 
                0.3 * np.sin(2 * np.pi * 2 * freq * t_arr) + 
                0.1 * np.sin(2 * np.pi * 3 * freq * t_arr))
        # Decay envelope
        decay = np.exp(-3 * t_arr / (d * (60/bpm)))
        audio[start:end] += (wave * decay) * 0.3
        
    # Normalize to 16-bit PCM range
    if np.max(np.abs(audio)) > 0:
        audio = (audio * 32767 / np.max(np.abs(audio))).astype(np.int16)
        
    byte_io = io.BytesIO()
    wav.write(byte_io, sample_rate, audio)
    return byte_io.getvalue()

# --- முக்கிய மாற்றம்: பியானோ ரோல் வரைபடம் ---
def plot_piano_roll(m_notes, m_times, m_durs):
    if not m_notes: return None
    fig, ax = plt.subplots(figsize=(10, 4))
    
    # வரைபடத்தின் பின்னணி நிறம்
    fig.patch.set_facecolor('black')
    ax.set_facecolor('#1a1a1a')
    
    # Grid lines - நோட்களைத் தெளிவாகக் காட்ட
    # கிடைமட்டக் கோடுகள் (ஆலஃபப்ஸ்பான் பயன்படுத்தி கருப்பு/வெள்ளை கட்டங்களைக் காட்டலாம், ஆனால் இங்கே எளிமைக்காக கோடுகள் மட்டும்)
    for note in range(min(m_notes)-1, max(m_notes
