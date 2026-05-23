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
    except:
        return ""

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
set_bg_image('image2.png')

# Supabase இணைப்பு விவரங்கள் (மாற்ற வேண்டாம்)
URL = "https://iryagjzdzqxqsqqhowcu.supabase.co"
KEY = "sb_publishable_eJqUvTMF80eliQTCLLVkYg_OrQiTCsG"
supabase: Client = create_client(URL, KEY)

# Session State Initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'current' not in st.session_state:
    st.session_state.current = None
if 'history_list' not in st.session_state:
    st.session_state.history_list = []

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
    if not notes:
        return None
    total_time = (max(times) + max(durs)) * (60 / bpm)
    audio = np.zeros(int(total_time * sample_rate) + 1000)
    for n, t, d in zip(notes, times, durs):
        freq = 440.0 * (2.0 ** ((n - 69) / 12.0))
        start = int(t * (60 / bpm) * sample_rate)
        end = int((t + d) * (60 / bpm) * sample_rate)
        t_arr = np.linspace(0, d * (60 / bpm), end - start, False)
        # Piano-like wave form with harmonics
        wave = (0.6 * np.sin(2 * np.pi * freq * t_arr) +
                0.3 * np.sin(2 * np.pi * 2 * freq * t_arr) +
                0.1 * np.sin(2 * np.pi * 3 * freq * t_arr))
        # Decay envelope
        decay = np.exp(-3 * t_arr / (d * (60 / bpm)))
        audio[start:end] += (wave * decay) * 0.3

    # Normalize to 16-bit PCM range
    if np.max(np.abs(audio)) > 0:
        audio = (audio * 32767 / np.max(np.abs(audio))).astype(np.int16)

    byte_io = io.BytesIO()
    wav.write(byte_io, sample_rate, audio)
    return byte_io.getvalue()

def plot_piano_roll(m_notes, m_times, m_durs):
    if not m_notes:
        return None
    fig, ax = plt.subplots(figsize=(10, 4))

    # வரைபடத்தின் பின்னணி நிறம்
    fig.patch.set_facecolor('black')
    ax.set_facecolor('#1a1a1a')

    # Grid lines - நோட்களைத் தெளிவாகக் காட்ட
    # கிடைமட்டக் கோடுகள்
    for note in range(min(m_notes) - 1, max(m_notes) + 2):
        ax.axhline(note, color='white', alpha=0.1, linewidth=0.5)

    # குத்துக்கோடுகள் (நேரம்)
    ax.grid(axis='x', color='white', alpha=0.1, linestyle='--', linewidth=0.5)

    # நோட்ஸை வரைதல்
    for n, t, d in zip(m_notes, m_times, m_durs):
        # Rectangle((x, y), width, height)
        ax.add_patch(plt.Rectangle((t, n - 0.4), d, 0.8, color='#1DB954', alpha=0.9, edgecolor='white', linewidth=0.5))

    # அச்சு லேபிள்கள் மற்றும் நிறங்கள்
    ax.set_xlabel("Time (Beats)", color='white', fontsize=10)
    ax.set_ylabel("MIDI Note", color='white', fontsize=10)
    ax.set_title("Piano Roll", color='white', fontsize=12)
    ax.tick_params(colors='white', labelsize=8)

    # வரைபடத்தின் எல்லைகளை (Scaling) நோட்ஸுக்கு ஏற்றவாறு அமைக்கவும்
    ax.set_xlim(0, max(m_times) + max(m_durs) + 1)
    ax.set_ylim(min(m_notes) - 2, max(m_notes) + 2)

    return fig

# --- 4. SIDEBAR ---
with st.sidebar:
    if not st.session_state.logged_in:
        st.header("Login / Sign Up 🔑")
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        c1, c2 = st.columns(2)
        if c1.button("Login"):
            try:
                # Supabase Login
                supabase.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()  # லாகின் ஆனவுடன் ரீரன் செய்யும்
            except Exception:
                st.error("Login Failed!")
        if c2.button("Sign Up"):
            try:
                # Supabase Sign Up
                supabase.auth.sign_up({"email": email, "password": pw})
                st.success("Account Created! You can now login.")
            except Exception:
                st.error("Sign up failed.")
    else:
        st.write(f"User: **{st.session_state.user_email}**")
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.logged_in = False
            st.rerun()

        st.markdown("---")
        st.header("Melody Settings")
        root_choice = st.selectbox("Root Note", list(ROOTS.keys()))
        mood_choice = st.selectbox("Select Mood", list(MOOD_PROPS.keys()))
        beats_choice = st.slider("Duration (Beats)", 4, 32, 16)

        st.markdown("---")
        st.subheader("Cloud History 📜")
        try:
            # --- முக்கிய திருத்தம் இங்கே: 100-வது வரியின் இறுதியில் `()` சேர்க்கப்பட்டுள்ளது ---
            # டேட்டாபேஸிலிருந்து பயனர் உருவாக்கிய மெலடிகளை எடுக்கும் செயல்பாடு
            res = supabase.table("melodies").select("*").execute()
            st.session_state.history_list = res.data
            if st.session_state.history_list:
                h_names = [m['melody_name'] for m in st.session_state.history_list]
                sel_name = st.selectbox("Load Previous", h_names)
                if st.button("Load History"):
                    # தேர்ந்தெடுக்கப்பட்ட மெலடியின் தரவை மீட்டெடுக்கும் செயல்பாடு
                    item = next(m for m in st.session_state.history_list if m['melody_name'] == sel_name)
                    n_dict = item['notes_data']
                    # நோட்ஸை வரிசைப்படுத்தி எடுப்பது முக்கியம்
                    s_notes = [n_dict[k] for k in sorted(n_dict.keys(), key=lambda x: int(x[1:]))]
                    s_times = [float(i) for i in range(len(s_notes))]  # Default 1 beat interval
                    s_durs = [1.0] * len(s_notes)

                    st.session_state.current = {
                        'id': item['melody_name'], 'notes': s_notes, 'times': s_times,
                        'durs': s_durs, 'bpm': 100, 'audio': synthesize_audio(s_notes, s_times, s_durs, 100)
                    }
                    st.success("Loaded!")
                    st.rerun()
        except Exception as db_error:
            st.sidebar.warning(f"Database connection failed: {db_error}")

# --- 5. MAIN APP ---
if st.session_state.logged_in:
    st.title("FLai: AI Music Assistant 🎹☁️")

    # புதிய இசை உருவாக்கம்
    if st.button("Generate & Save🤖"):
        props = MOOD_PROPS[mood_choice]
        root_midi = ROOTS[root_choice]
        scale = [root_midi + i for i in props['scale']]

        m_notes, m_times, m_durs = [], [], []
        curr = 0.0
        while curr < beats_choice:
            note = random.choice(scale)
            dur = random.choice(props['durations'])
            if curr + dur > beats_choice:
                dur = float(beats_choice - curr)
            m_notes.append(note); m_times.append(curr); m_durs.append(dur); curr += dur

        melody_id = f"FLai_{mood_choice.split()[-1]}_{random.randint(100, 999)}"
        notes_dict = {f"n{i+1}": n for i, n in enumerate(m_notes)}

        # Cloud database-இல் சேமிக்கும் செயல்பாடு
        try:
            supabase.table("melodies").insert(
                {"melody_name": melody_id, "mood": mood_choice, "notes_data": notes_dict}).execute()
            st.session_state.current = {
                'id': melody_id, 'notes': m_notes, 'times': m_times, 'durs': m_durs, 'bpm': props['bpm'],
                'audio': synthesize_audio(m_notes, m_times, m_durs, props['bpm'])
            }
            st.success(f"Saved: {melody_id}")
        except Exception as e:
            st.error(f"Cloud Save Error: {e}")

    # தற்போதைய மெலடியைக் காட்சிப்படுத்துதல் (Piano Roll & Audio)
    if st.session_state.current:
        curr = st.session_state.current
        st.markdown(f"### 🎵 Now Playing: {curr['id']}")

        fig = plot_piano_roll(curr['notes'], curr['times'], curr['durs'])

        col1, col2 = st.columns([3, 1])
        with col1:
            if fig: st.pyplot(fig)  # பியானோ ரோலைக் காட்டுதல்
        with col2:
            # ஆடியோ பிளேயர்
            st.audio(curr['audio'], format='audio/wav')
            st.write(f"BPM: {curr['bpm']}")
            st.write(f"Notes: {len(curr['notes'])}")
else:
    st.title("Welcome to FLai 🎹")
    st.info("Sidebar-இல் Login செய்து உங்கள் இசையை உருவாக்கத் தொடங்குங்கள்!")
