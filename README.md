# 🎹 MIDI Processing Pipeline

This repository provides a set of scripts to process expressive piano performance recordings by:

- Extracting audio from video recordings
- Transcribing audio into MIDI using [`transkun`](https://github.com/yujiany/transkun)
- Aligning ground truth MIDI to transcribed MIDI using anchor matching
- Rendering MIDI back to audio using FluidSynth
- Replacing video audio tracks with aligned MIDI audio
- Visualizing note-level overlaps between ground truth and transcription

---
🛠️ Usage
1. Align Ground Truth MIDI


```bash
python correction.py \
  --gt "/path/to/original_gt.mid" \
  --transkun "/path/to/transkun_output.mid" \
  --output "/path/to/aligned_output.mid"
```

2. Convert MIDI to Audio (WAV)

```bash
python toaudio.py \
  --midi "/path/to/aligned_output.mid" \
  --output "/path/to/output_audio.wav"
```

3. Visualize Overlap Between Two MIDI Files(can decide to chosse display_mode in time or frame, and also the start time and end time, if set it to None, the result will be showing the whole piece.)

```bash
python overlap.py \
  --transkun "/path/to/transkun.mid" \
  --aligned "/path/to/aligned.mid" \
  --output "/path/to/output.png" \
  --start 70 \
  --end 80 \
  --display_mode frame \
  --fps 25
```

4. Batch Processing of All Cases

```bash
python run_all.py
```

📦 Output Folder Structure (per case)

caseX/
├── audio.mp3              # Extracted from original MP4
├── transkun_output.mid    # MIDI from transkun
├── aligned_output.mid     # Time-aligned ground truth MIDI
├── aligned_output.wav     # Synthesized audio from aligned MIDI
├── output_aligned.mp4     # Final video with aligned audio
└── overlap.png            # Note-level comparison visualization


