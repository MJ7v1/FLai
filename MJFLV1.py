import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import io
import random
import base64
from supabase import create_client, Client
import scipy.io.wavfile as wav

# --- 1. பின்னணிப் படத்தை அமைக்கும் பகுதி (Background Setup) ---
def get_base64(bin_file):
    """படத்தை Base64 ஆக மாற்றும் செயல்பாடு"""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_bg_image(image_file):
    """CSS மூலம் பின்னணியை அமைக்கும் செயல்பாடு"""
    try:
        bin_str = get_base64(image_file)
        page_bg_img = f'''
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        /* எழுத்துக்கள் மற்றும் பட்டன்கள் தெளிவாகத் தெரிய CSS */
        h1, h2, h3, p, span, .stMarkdown, .stText, label {{
            color: white !important;
            text-shadow: 2px 2px 4px #000000;
        }}
        /* Sidebar உரை நிறம் */
        [data-testid="stSidebar"] {{
            background-color: rgba(0, 0, 0, 0.7); /* சற்று வெளிப்படையான கருப்பு நிறம் */
        }}
        </style>
        '''
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"படம் '{image_file}' கிடைக்கவில்லை. பின்னணிப் படம் இல்லாமல் ஆப் இயங்கும்.")

# --- 2. தொடக்க நிலை அமைப்புகள் (Streamlit Config) ---
st.set_page_config(page_title="FLai V3.5", layout="wide")

# பின்னணியை செட் செய்கிறோம் (Assets folder-இல் படம் இருக்க வேண்டும்)
set_bg_image('assets/1000191225.png')

# --- 3. சுபபேஸ் இணைப்பு (Supabase Setup) ---
URL = "https://iryagjzdzqxqsqqhowcu.supabase.co"
KEY = "sb_publishable_eJqUvTMF80eliQTCLLVkYg_OrQiTCsG"
supabase: Client = create_client(URL, KEY)

# Session State மேலாண்மை
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'current' not in st.session_state:
    st.session_state.current = None

# --- 4. டேட்டா மற்றும் மியூசிக் லாஜிக் ---
MOOD_PROPS = {
    "😊 Happy": {"scale": [0, 2, 4, 5, 7, 9, 11], "bpm": 124, "velocity": 100, "pattern": [0, 4, 7, 12], "durations": [0.5, 0.5]},
    "😢 Sad": {"scale": [0, 2, 3, 5, 7, 8, 10], "bpm": 60, "velocity": 60, "pattern": [0, 2, 3, 5], "durations": [1.0, 2.0]},
    "😱 Horror": {"scale": [0, 1, 6, 7, 11], "bpm": 45, "velocity": 50, "pattern": [0, 1, 6], "durations": [0.5, 2.0, 4.0]},
    "🎤 RAP": {"scale": [0, 1, 3, 5, 7, 8, 10], "bpm": 90, "velocity": 110, "pattern": [0, 0, 3, 0], "durations": [0.25, 0.5]}
}
ROOTS = {"C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71}

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
    wav.write(byte_io, sample_rate, audio)
    return byte_io.getvalue()

def plot_piano_roll(m_notes, m_times, m_durs):
    if not m_notes: return None
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')
    for n, t, d in zip(m_notes, m_times, m_durs):
        ax.add_patch(plt.Rectangle((t, n-0.4), d, 0.8, color='#1DB954'))
    ax.set_xlabel("Time (Beats)", color='white')
    ax.set_ylabel("MIDI Note", color='white')
    ax.tick_params(colors='white')
    return fig

# --- 5. SIDEBAR (Login & Settings) ---
with st.sidebar:
    if not st.session_state.logged_in:
        st.header("Login 🔑")
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()
            except Exception as e:
                st.error("Login Failed!")
    else:
        st.write(f"Logged in as: **{st.session_state.user_email}**")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown("---")
        root_choice = st.selectbox("Root Note", list(ROOTS.keys()))
        mood_choice = st.selectbox("Select Mood", list(MOOD_PROPS.keys()))
        beats_choice = st.slider("Beats", 4, 32, 16)

# --- 6. MAIN APP ---
if st.session_state.logged_in:
    st.title("FLai: AI Music Assistant 🎹☁️")
    
    if st.button("Generate & Save 🤖"):
        props = MOOD_PROPS[mood_choice]
        root_midi = ROOTS[root_choice]
        scale = [root_midi + i for i in props['scale']]
        
        m_notes, m_times, m_durs = [], [], []
        curr = 0
        while curr < beats_choice:
            note = random.choice(scale) + random.choice(props['pattern'])
            dur = random.choice(props['durations'])
            if curr + dur > beats_choice: dur = float(beats_choice - curr)
            m_notes.append(note); m_times.append(curr); m_durs.append(dur); curr += dur

        melody_id = f"FLai_{random.randint(100,999)}"
        st.session_state.current = {
            'id': melody_id, 'notes': m_notes, 'times': m_times, 'durs': m_durs, 'bpm': props['bpm'],
            'audio': synthesize_audio(m_notes, m_times, m_durs, props['bpm'])
        }
        st.success("Generated Successfully!")

    if st.session_state.current:
        curr = st.session_state.current
        st.subheader(f"Track: {curr['id']}")
        fig = plot_piano_roll(curr['notes'], curr['times'], curr['durs'])
        st.pyplot(fig)
        st.audio(curr['audio'], format='audio/wav')
else:
    st.title("Welcome to FLai 🎹")
    st.info("Sidebar-இல் Login செய்து தொடங்குங்கள்!")

