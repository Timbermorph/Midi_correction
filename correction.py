from pathlib import Path
import pretty_midi
import numpy as np

# === Configuration ===
# Ground truth MIDI (recorded piano, usually drifting)
gt_midi_path = Path("/storage/user/ljia/folder_for_share/0G65V8B2A5HSW8L_1752833517.mid")

# Transkun MIDI (aligned to audio)
transkun_midi_path = Path("/storage/user/ljia/folder_for_share/cam00045D6F85000_transcribed.mid")

# Output path for aligned GT MIDI
output_path = Path("groundtruth_aligned_linear.mid")

# === Step 1: Note extraction ===
def extract_notes(midi_path):
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    notes = []
    for inst in midi.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            notes.append((n.start, n.end, n.pitch))
    return notes, midi

gt_notes, gt_midi = extract_notes(gt_midi_path)
transkun_notes, _ = extract_notes(transkun_midi_path)

epsilon = 0.01  # 10ms tolerance for "simultaneous" note grouping

# === Step 2: Get first GT note group (could be single note or chord) ===
first_gt_time = min(n[0] for n in gt_notes)
gt_first_pitches = [pitch for start, end, pitch in gt_notes if abs(start - first_gt_time) < epsilon]
print(f"[GT First Anchor] Time = {first_gt_time:.3f}, Pitches = {gt_first_pitches}")

# === Step 3: Find matching first anchor in Transkun MIDI ===
first_aligned_time = None
transkun_notes_sorted = sorted(transkun_notes, key=lambda x: x[0])

for i in range(len(transkun_notes_sorted)):
    current_time = transkun_notes_sorted[i][0]
    group = [note for note in transkun_notes if abs(note[0] - current_time) < epsilon]
    group_pitches = [n[2] for n in group]
    match_count = sum(1 for p in gt_first_pitches if p in group_pitches)
    match_ratio = match_count / len(gt_first_pitches)
    if match_ratio >= 0.8:
        first_aligned_time = current_time
        print(f"[First Anchor Match] Transkun time = {current_time:.3f}, Pitches at this time = {group_pitches}")
        break

if first_aligned_time is None:
    raise RuntimeError("❌ Failed to find matching first anchor in Transkun MIDI.")

# === Step 4: Get last GT note group ===
last_gt_time = max(n[0] for n in gt_notes)
gt_last_pitches = [pitch for start, end, pitch in gt_notes if abs(start - last_gt_time) < epsilon]
print(f"[GT Last Anchor] Time = {last_gt_time:.3f}, Pitches = {gt_last_pitches}")

# === Step 5: Find matching last anchor in Transkun MIDI ===
last_aligned_time = None
transkun_notes_sorted_rev = sorted(transkun_notes, key=lambda x: -x[0])  # descending time

for i in range(len(transkun_notes_sorted_rev)):
    current_time = transkun_notes_sorted_rev[i][0]
    if current_time < first_aligned_time:  # ensure order is preserved
        break
    group = [note for note in transkun_notes if abs(note[0] - current_time) < epsilon]
    group_pitches = [n[2] for n in group]
    match_count = sum(1 for p in gt_last_pitches if p in group_pitches)
    match_ratio = match_count / len(gt_last_pitches)
    if match_ratio >= 0.8:
        last_aligned_time = current_time
        print(f"[Last Anchor Match] Transkun time = {current_time:.3f}, Pitches at this time = {group_pitches}")
        break

if last_aligned_time is None:
    raise RuntimeError("❌ Failed to find matching last anchor in Transkun MIDI.")

# === Step 6: Fit linear time correction function ===
t0_gt = first_gt_time
t1_gt = last_gt_time
t0_aligned = first_aligned_time
t1_aligned = last_aligned_time

a = (t1_aligned - t0_aligned) / (t1_gt - t0_gt)
b = t0_aligned - a * t0_gt

print(f"[Linear Fit] t_aligned = {a:.6f} * t_gt + {b:.6f}")

# === Step 7: Apply correction to all GT notes ===
for inst in gt_midi.instruments:
    for note in inst.notes:
        note.start = a * note.start + b
        note.end = a * note.end + b

# === Step 8: Save aligned MIDI ===
gt_midi.write(str(output_path))
print(f"✅ Saved aligned GT MIDI to: {output_path}")
