import pretty_midi
from scipy.io.wavfile import write
import numpy as np

# ==== ?????? ====
midi_path = "/storage/user/ljia/folder_for_share/groundtruth_aligned_linear.mid"
wav_path = "/storage/user/ljia/folder_for_share/aligned_output.wav"

# ==== ?? MIDI ????? ====
midi = pretty_midi.PrettyMIDI(midi_path)
audio = midi.fluidsynth(fs=44100)  # ? midi.synthesize(),???? fluidsynth

# ==== ?? WAV ?? ====
audio_int16 = np.int16(audio / np.max(np.abs(audio)) * 32767)  # ???????16???
write(wav_path, 44100, audio_int16)

print(f"? ??????: {wav_path}")
