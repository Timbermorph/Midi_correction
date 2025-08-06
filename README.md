🛠️ Usage
1. Align Ground Truth MIDI
Use correction.py to align a ground truth MIDI file (e.g., recorded from piano) to a transkun-transcribed MIDI file based on first and last anchor notes.

bash
python correction.py \
  --gt "/path/to/original_gt.mid" \
  --transkun "/path/to/transkun_output.mid" \
  --output "/path/to/aligned_output.mid"
2. Convert MIDI to Audio (WAV)
Use toaudio.py to render an aligned MIDI file into an audio waveform using FluidSynth (default 44.1kHz).

bash
python toaudio.py \
  --midi "/path/to/aligned_output.mid" \
  --output "/path/to/output_audio.wav"
3. Visualize MIDI Overlap
Use overlap.py to compare the transkun MIDI and the aligned GT MIDI at the note level. It will generate a color-coded image showing matched/unmatched notes across time or frame index.

bash
python overlap.py \
  --transkun "/path/to/transkun.mid" \
  --aligned "/path/to/aligned.mid" \
  --output "/path/to/output.png" \
  --start 70 \
  --end 80 \
  --display_mode frame \
  --fps 25
