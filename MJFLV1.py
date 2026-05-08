import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from midiutil import MIDIFile
import io
import random
import os
from supabase import create_client, Client

# --- 1. சுபபேஸ் இணைப்பு (Supabase Setup) ---
URL: str = "https://iryagjzdzqxqsqqhowcu.supabase.co"
KEY: str = "sb_publishable_eJqUvTMF80eliQTCLLVkYg_OrQiTCsG"
supabase: Client = create_client(URL, KEY)

# --- 2. தொடக்க நிலை அமைப்புகள் (Initialization) ---
if 'current' not in st.session_state:
    st.session_state.current = None
if 'history_list' not in st.session_state:
    st.session_state.history_list = []

# --- 3. AI மூட் இன்ஜின் ---
MOOD_PROPS = {
    "😊 Happy": {"scale": [0, 2, 4, 5, 7, 9, 11], "bpm": 124, "velocity": 100, "pattern": [0, 4, 7, 12], "durations": [0.5, 0.5]},
    "😢 Sad": {"scale": [0, 2, 3, 5, 7, 8, 10], "bpm": 60, "velocity": 60, "pattern": [0, 2, 3, 5], "durations": [1.0, 2.0]},
    "😱 Horror": {"scale": [0, 1, 6, 7, 11], "bpm": 45, "velocity": 50, "pattern": [0, 1, 6], "durations": [0.5, 2.0, 4.0]},
    "🎤 RAP": {"scale": [0, 1, 3, 5, 7, 8, 10], "bpm": 90, "velocity": 110, "pattern": [0, 0, 3, 0], "durations": [0.25, 0.5]}
}
ROOTS = {"C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71}

# --- 4. பயனுள்ள செயல்பாடுகள் ---

def plot_piano_roll(m_notes, m_times, m_durs):
    if not m_notes: return None
    fig, ax = plt.subplots(figsize=(12, 6))
    for note in range(min(m_notes)-2, max(m_notes)+3):
        is_black = (note % 12) in [1, 3, 6, 8, 10]
        color = '#eeeeee' if not is_black else '#bbbbbb'
        ax.axhspan(note-0.5, note+0.5, facecolor=color, alpha=0.3)
    ax.grid(which='both', color='black', linestyle='-', linewidth=0.5, alpha=0.2)
    ax.set_xticks(np.arange(0, max(m_times)+2, 0.5))
    for n, t, d in zip(m_notes, m_times, m_durs):
        ax.add_patch(plt.Rectangle((t, n-0.4), d, 0.8, color='#1DB954', zorder=3))
    return fig

def synthesize_audio(notes, times, durs, bpm):
    sample_rate = 44100
    total_time = (max(times) + max(durs)) * (60/bpm)
    audio = np.zeros(int(total_time * sample_rate))
    for n, t, d in zip(notes, times, durs):
        freq = 440.0 * (2.0 ** ((n - 69) / 12.0))
        start, end = int(t * (60/bpm) * sample_rate), int((t + d) * (60/bpm) * sample_rate)
        t_arr = np.linspace(0, d * (60/bpm), end - start, False)
        envelope = np.sin(np.pi * np.linspace(0, 1, end-start))
        audio[start:end] += (np.sin(2 * np.pi * freq * t_arr) * envelope) * 0.3
    audio = (audio * 32767 / (np.max(np.abs(audio)) if np.max(np.abs(audio)) > 0 else 1)).astype(np.int16)
    byte_io = io.BytesIO()
    import scipy.io.wavfile as wav
    wav.write(byte_io, sample_rate, audio)
    return byte_io.getvalue()

# --- 5. UI வடிவமைப்பு ---
st.set_page_config(page_title="FLai V3.5 (DB Edition)", layout="wide")
st.title("FLai: AI Music Assistant (Professional Database) 🎹☁️")

with st.sidebar:
    st.header("Settings")
    root_choice = st.selectbox("Root Note", list(ROOTS.keys()))
    mood_choice = st.selectbox("Select Mood", list(MOOD_PROPS.keys()))
    beats_choice = st.slider("Duration (Beats)", 4, 32, 16)
    
    st.markdown("---")
    st.subheader("History from Cloud 📜")
    
    try:
        response = supabase.table("melodies").select("*").execute()
        st.session_state.history_list = response.data
    except:
        st.error("Database connection failed!")

    if st.session_state.history_list:
        history_names = [m['melody_name'] for m in st.session_state.history_list]
        selected_name = st.selectbox("Select previous melody", history_names)
        
        if st.button("Load History"):
            item = next(m for m in st.session_state.history_list if m['melody_name'] == selected_name)
            notes_dict = item['notes_data']
            sorted_keys = sorted(notes_dict.keys(), key=lambda x: int(x[1:]))
            sorted_notes = [notes_dict[k] for k in sorted_keys]
            
            m_times = list(np.arange(0, len(sorted_notes) * 1.0, 1.0))
            m_durs = [1.0] * len(sorted_notes)
            bpm = 100 
            
            audio_data = synthesize_audio(sorted_notes, m_times, m_durs, bpm)
            
            st.session_state.current = {
                'id': item['melody_name'],
                'notes': sorted_notes,
                'times': m_times,
                'durs': m_durs,
                'bpm': bpm,
                'audio': audio_data
            }
            st.rerun()

# --- 6. பிரதான செயல்பாடு ---
if st.button("Generate & Save to Cloud 🤖"):
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

    notes_dict = {f"n{i+1}": n for i, n in enumerate(m_notes)}
    melody_id = f"FLai_{mood_choice.split()[-1]}_{random.randint(100,999)}"

    db_data = {"melody_name": melody_id, "mood": mood_choice, "notes_data": notes_dict}
    supabase.table("melodies").insert(db_data).execute()

    st.session_state.current = {
        'id': melody_id, 'notes': m_notes, 'times': m_times, 'durs': m_durs, 'bpm': props['bpm'],
        'audio': synthesize_audio(m_notes, m_times, m_durs, props['bpm'])
    }
    st.success(f"Saved to Cloud as {melody_id}!")

# --- 7. Display ---
if st.session_state.current:
    curr = st.session_state.current
    st.subheader(f"Track: {curr['id']}")
    
    fig = plot_piano_roll(curr['notes'], curr['times'], curr['durs'])
    col1, col2 = st.columns([2, 1])
    with col1:
        if fig: st.pyplot(fig)
    with col2:
        st.audio(curr['audio'], format='audio/wav')
