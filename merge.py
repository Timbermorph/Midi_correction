import pretty_midi
import pygame
import time

# ????
midi_path1 = "/storage/user/ljia/folder_for_share/cam00045D6F85000_transcribed.mid"
midi_path2 = "/storage/user/ljia/folder_for_share/groundtruth_aligned_linear.mid"
merged_path = "/storage/user/ljia/folder_for_share/merged2.mid"

# ???? MIDI ??
midi1 = pretty_midi.PrettyMIDI(midi_path1)
midi2 = pretty_midi.PrettyMIDI(midi_path2)

# ??? MIDI
merged_midi = pretty_midi.PrettyMIDI()

# ??? MIDI ??????
inst1 = midi1.instruments[0]
inst1.name = "Original"
merged_midi.instruments.append(inst1)

# ??? MIDI ??????
inst2 = midi2.instruments[0]
inst2.name = "Aligned"
merged_midi.instruments.append(inst2)

# ??????
merged_midi.write(merged_path)
print(f"? ????,??????:{merged_path}")
