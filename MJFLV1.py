import streamlit as st
import matplotlib.pyplot as plt
from midiutil import MIDIFile
import io
import random
import time
import os

# --- 1. எண்ணிக்கைக்கான கோப்பு தர்க்கம் (File Persistence) ---
COUNT_FILE = "melody_count.txt"


def get_next_count():
    if not os.path.exists(COUNT_FILE):
        with open(COUNT_FILE, "w") as f:
            f.write("0")
        return 0
    with open(COUNT_FILE, "r") as f:
        count = int(f.read())
    return count


def save_count(count):
    with open(COUNT_FILE, "w") as f:
        f.write(str(count))


# --- 2. இசை தரவுகள் ---
MOOD_DATA = {
    "😢 Sad": {"instruments": "Piano, Strings", "scale_key": "Minor"},
    "😊 Happy": {"instruments": "Pluck, Marimba", "scale_key": "Major"},
    "😱 Horror": {"instruments": "Dark Pad, Drone", "scale_key": "Minor"},
    "🎬 BGM": {"instruments": "Brass, Strings", "scale_key": "Mixolydian"},
    "🎤 RAP": {"instruments": "808 Bass, Keys", "scale_key": "Phrygian"}
}

SCALES = {
    "Major": [0, 2, 4, 5, 7, 9, 11],
    "Minor": [0, 2, 3, 5, 7, 8, 10],
    "Phrygian": [0, 1, 3, 5, 7, 8, 10],
    "Mixolydian": [0, 2, 4, 5, 7, 9, 10]
}

ROOTS = {"C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71}


# --- 3. செயல்பாடுகள் ---
def create_midi(notes, times, durations, is_bass=False):
    mf = MIDIFile(1)
    mf.addTempo(0, 0, 60)
    for n, t, d in zip(notes, times, durations):
        # Bass நோட்களுக்கு சத்தம் (Velocity) சற்று குறைவாக இருந்தால் நன்றாக இருக்கும்
        velocity = 80 if is_bass else 100
        mf.addNote(0, 0, n, t, d, velocity)
    mem_file = io.BytesIO()
    mf.writeFile(mem_file)
    return mem_file.getvalue()


def plot_piano_roll(m_data, b_data, total_beats):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.grid(True, which='both', linestyle=':', alpha=0.5, color='gray')

    # Melody Notes (Green)
    for n, t, d in zip(m_data['notes'], m_data['times'], m_data['durs']):
        ax.add_patch(plt.Rectangle((t, n - 0.4), d, 0.8, color='#50fa7b', label='Melody', alpha=0.8))

    # Bass Notes (Blue)
    for n, t, d in zip(b_data['notes'], b_data['times'], b_data['durs']):
        ax.add_patch(plt.Rectangle((t, n - 0.4), d, 0.8, color='#8be9fd', label='Bass', alpha=0.6))

    ax.set_ylim(30, 80)  # Bass மற்றும் Melody இரண்டையும் காட்ட விஸ்தரிக்கப்பட்டது
    ax.set_xlim(0, total_beats)
    ax.set_facecolor('#1e1e1e')
    st.pyplot(fig)


# --- 4. UI ---
st.set_page_config(page_title="AI FL Helper Pro V2.4", layout="wide")
st.title("AI Music Assistant V2.4 🎧 (Melody + Bass)")

if 'history' not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("Settings ⚙️")
    root_choice = st.selectbox("Root Note", list(ROOTS.keys()))
    mood_choice = st.selectbox("Mood Type", list(MOOD_DATA.keys()))
    beats_choice = st.selectbox("Duration (Seconds)", [4, 8, 16])

    st.markdown("---")
    st.header("History 📜")
    for idx, item in enumerate(st.session_state.history[::-1]):
        if st.button(f"🎼 {item['mjv_id']} ({item['desc']})", key=f"hist_{idx}"):
            st.session_state.current_melody = item

if st.button(f"Generate Melody & Bass 🎹"):
    with st.spinner('Creating harmony...'):
        time.sleep(0.5)

        # 1. கோப்பிலிருந்து எண்ணிக்கையை எடுத்து புதுப்பித்தல்
        count = get_next_count() + 1
        save_count(count)
        mjv_id = f"mjv{count}"

        root_midi = ROOTS[root_choice]
        scale_notes = [root_midi + i for i in SCALES[MOOD_DATA[mood_choice]['scale_key']]]

        # 2. Melody உருவாக்கம்
        m_notes, m_times, m_durs = [], [], []
        curr = 0
        while curr < beats_choice:
            dur = random.choice([0.5, 1.0])
            if curr + dur > beats_choice: dur = beats_choice - curr
            if curr == 0 or random.random() > 0.25:
                m_notes.append(random.choice(scale_notes))
                m_times.append(curr)
                m_durs.append(dur)
            curr += dur

        # 3. Bass உருவாக்கம் (மெலடிக்கு ஏற்றவாறு)
        b_notes, b_times, b_durs = [], [], []
        for b in range(0, beats_choice, 2):  # ஒவ்வொரு 2 பீட்க்கும் ஒரு பாஸ் நோட்
            b_notes.append(root_midi - 24)  # 2 Octaves கீழே
            b_times.append(float(b))
            b_durs.append(2.0)

        # 4. MIDI ஒருங்கிணைப்பு
        full_notes = m_notes + b_notes
        full_times = m_times + b_times
        full_durs = m_durs + b_durs

        new_entry = {
            'mjv_id': mjv_id, 'notes': m_notes, 'times': m_times, 'durs': m_durs,
            'bass': {'notes': b_notes, 'times': b_times, 'durs': b_durs},
            'beats': beats_choice, 'desc': mood_choice,
            'midi': create_midi(full_notes, full_times, full_durs)
        }
        st.session_state.current_melody = new_entry
        st.session_state.history.append(new_entry)

if 'current_melody' in st.session_state:
    m = st.session_state.current_melody
    st.subheader(f"Preview: {m['mjv_id']} ({m['desc']})")
    plot_piano_roll(m, m['bass'], m['beats'])
    st.download_button("Download MIDI 📥", m['midi'], f"{m['mjv_id']}.mid")