import argparse
import pretty_midi
from scipy.io.wavfile import write
import numpy as np
from pathlib import Path

def midi_to_audio(midi_path, wav_path):
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    audio = midi.fluidsynth(fs=44100) 
    audio_int16 = np.int16(audio / np.max(np.abs(audio)) * 32767)
    
    wav_path = Path(wav_path)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    write(wav_path, 44100, audio_int16)
    print(f"Audio saved to: {wav_path} (rendered with fluidsynth)")

# === CLI entry ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render MIDI to audio (.wav) using fluidsynth")
    parser.add_argument("--midi", type=str, required=True, help="Input MIDI file path")
    parser.add_argument("--output", type=str, required=True, help="Output WAV file path")
    args = parser.parse_args()

    midi_to_audio(args.midi, args.output)
