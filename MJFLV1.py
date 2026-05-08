import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from midiutil import MIDIFile
import io
import random
import os
import base64

# --- 1. கோப்பு மேலாண்மை ---
COUNT_FILE = "melody_count.txt"

def get_next_count():
    if not os.path.exists(COUNT_FILE): return 0
    try:
        with open(COUNT_FILE, "r") as f: return int(f.read())
    except: return 0

def save_count(count):
    with open(COUNT_FILE, "w") as f: f.write(str(count))

# --- 2. AI மூட் இன்ஜின் (AI Mood Engine) ---
# இங்குதான் AI-க்கு ஒவ்வொரு மூடுக்கும் என்னென்ன செய்ய வேண்டும் என்ற 'பயிற்சி' விதிகள் உள்ளன.
MOOD_PROPS = {
    "😊 Happy": {
        "scale": [0, 2, 4, 5, 7, 9, 11], # Major
        "bpm": 124,
        "velocity": 100,
        "pattern": [0, 4, 7, 12], # Arpeggio pattern
        "durations": [0.5, 0.5]
    },
    "😢 Sad": {
        "scale": [0, 2, 3, 5, 7, 8, 10], # Minor
        "bpm": 60,
        "velocity": 60,
        "pattern": [0, 2, 3, 5], # Step-by-step
        "durations": [1.0, 2.0]
    },
    "😱 Horror": {
        "scale": [0, 1, 6, 7, 11], # Dissonant (Tritone focus)
        "bpm": 45,
        "velocity": 50,
        "pattern": [0, 1, 6], # Scarier jumps
        "durations": [0.5, 2.0, 4.0]
    },
    "🎤 RAP": {
        "scale": [0, 1, 3, 5, 7, 8, 10], # Phrygian
        "bpm": 90,
        "velocity": 110,
        "pattern": [0, 0, 3, 0], # Rhythmic focus
        "durations": [0.25, 0.5]
    }
}

ROOTS = {"C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71}

# --- 3. பியானோ ரோல் வரைபடம் (Visualizer) ---
def plot_piano_roll(m_notes, m_times, m_durs):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # பியானோ கருப்பு/வெள்ளை கட்டைகளை உருவாக்குதல் 🎹
    for note in range(min(m_notes)-2, max(m_notes)+3):
        is_black = (note % 12) in [1, 3, 6, 8, 10]
        color = '#eeeeee' if not is_black else '#bbbbbb' # White and Grey keys
        ax.axhspan(note-0.5, note+0.5, facecolor=color, alpha=0.3)

    # கிரிட் கோடுகளை இருமடங்கு அதிகரித்தல் (Gridlines) 🏁
    ax.grid(which='both', color='black', linestyle='-', linewidth=0.5, alpha=0.2)
    ax.set_xticks(np.arange(0, max(m_times)+2, 0.5)) # 0.5 இடைவெளியில் கோடுகள்

    # நோட்களை வரைதல்
    for n, t, d in zip(m_notes, m_times, m_durs):
        ax.add_patch(plt.Rectangle((t, n-0.4), d, 0.8, color='#1DB954', zorder=3))

    ax.set_facecolor('white')
    ax.set_xlabel("Beats (Time)")
    ax.set_ylabel("MIDI Notes (Pitch)")
    plt.title("FLai Professional Piano Roll")
    return fig

# --- 4. ஆடியோ பிளேபேக் (Simple Synthesizer) ---
def synthesize_audio(notes, times, durs, bpm):
    # மிக எளிமையான சின்த் ஒலியை (Sine Wave) உருவாக்குகிறது
    sample_rate = 44100
    total_time = (max(times) + max(durs)) * (60/bpm)
    audio = np.zeros(int(total_time * sample_rate))
    
    for n, t, d in zip(notes, times, durs):
        freq = 440.0 * (2.0 ** ((n - 69) / 12.0))
        start = int(t * (60/bpm) * sample_rate)
        end = int((t + d) * (60/bpm) * sample_rate)
        t_arr = np.linspace(0, d * (60/bpm), end - start, False)
        # Fade in/out to prevent clicks
        envelope = np.sin(np.pi * np.linspace(0, 1, end-start)) 
        wave = np.sin(2 * np.pi * freq * t_arr) * envelope
        audio[start:end] += wave * 0.3

    # Normalize audio
    audio = (audio * 32767 / np.max(np.abs(audio))).astype(np.int16)
    import scipy.io.wavfile as wav
    byte_io = io.BytesIO()
    wav.write(byte_io, sample_rate, audio)
    return byte_io.getvalue()

# --- 5. UI வடிவமைப்பு ---
st.set_page_config(page_title="FLai V3.0", layout="wide")
st.title("FLai: AI Music Assistant V3.0 🎹🎼")

with st.sidebar:
    st.header("Settings")
    root_choice = st.selectbox("Root Note", list(ROOTS.keys()))
    mood_choice = st.selectbox("Select Mood", list(MOOD_PROPS.keys()))
    beats_choice = st.slider("Duration (Beats)", 4, 32, 16)

if st.button("Generate & Train AI 🤖"):
    props = MOOD_PROPS[mood_choice]
    root_midi = ROOTS[root_choice]
    scale = [root_midi + i for i in props['scale']]
    
    # Melody Generation Logic
    m_notes, m_times, m_durs = [], [], []
    curr = 0
    while curr < beats_choice:
        # AI Training Pattern-ஐப் பயன்படுத்துதல்
        note = random.choice(scale) + random.choice(props['pattern'])
        dur = random.choice(props['durations'])
        if curr + dur > beats_choice: dur = float(beats_choice - curr)
        
        m_notes.append(note)
        m_times.append(curr)
        m_durs.append(dur)
        curr += dur

    # MIDI உருவாக்குதல்
    mf = MIDIFile(1)
    mf.addTempo(0, 0, props['bpm'])
    for n, t, d in zip(m_notes, m_times, m_durs):
        mf.addNote(0, 0, n, t, d, props['velocity'])
    
    midi_file = io.BytesIO()
    mf.writeFile(midi_file)
    
    # Audio உருவாக்குதல்
    audio_data = synthesize_audio(m_notes, m_times, m_durs, props['bpm'])
    
    # எண்ணிக்கை சேமிப்பு
    count = get_next_count() + 1
    save_count(count)
    
    st.session_state.current = {
        'id': f"FLai_{mood_choice.split()[1]}_{count}",
        'midi': midi_file.getvalue(),
        'audio': audio_data,
        'plot': plot_piano_roll(m_notes, m_times, m_durs)
    }

if 'current' in st.session_state:
    c = st.session_state.current
    st.subheader(f"Current Track: {c['id']}")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.pyplot(c['plot'])
    with col2:
        st.write("### Playback 🔊")
        st.audio(c['audio'], format='audio/wav')
        st.download_button("Download MIDI 📥", c['midi'], f"{c['id']}.mid")

