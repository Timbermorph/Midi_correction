import argparse
from pathlib import Path
import pretty_midi
import numpy as np

def extract_notes(midi_path):
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    notes = []
    for inst in midi.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            notes.append((n.start, n.end, n.pitch))
    return notes, midi

def align_gt_to_transkun(gt_midi_path, transkun_midi_path, output_path, epsilon=0.01):
    gt_notes, gt_midi = extract_notes(gt_midi_path)
    transkun_notes, _ = extract_notes(transkun_midi_path)

    # === First Anchor
    first_gt_time = min(n[0] for n in gt_notes)
    gt_first_pitches = [pitch for start, end, pitch in gt_notes if abs(start - first_gt_time) < epsilon]
    print(f"[GT First Anchor] Time = {first_gt_time:.3f}, Pitches = {gt_first_pitches}")

    first_aligned_time = None
    transkun_notes_sorted = sorted(transkun_notes, key=lambda x: x[0])

    for note in transkun_notes_sorted:
        current_time = note[0]
        group = [n for n in transkun_notes if abs(n[0] - current_time) < epsilon]
        group_pitches = [n[2] for n in group]
        match_count = sum(1 for p in gt_first_pitches if p in group_pitches)
        match_ratio = match_count / len(gt_first_pitches)
        if match_ratio >= 0.8:
            first_aligned_time = current_time
            print(f"[First Anchor Match] Transkun time = {current_time:.3f}, Pitches at this time = {group_pitches}")
            break

    if first_aligned_time is None:
        raise RuntimeError("Failed to find matching first anchor in Transkun MIDI.")

    # === Last Anchor
    last_gt_time = max(n[0] for n in gt_notes)
    gt_last_pitches = [pitch for start, end, pitch in gt_notes if abs(start - last_gt_time) < epsilon]
    print(f"[GT Last Anchor] Time = {last_gt_time:.3f}, Pitches = {gt_last_pitches}")

    last_aligned_time = None
    transkun_notes_sorted_rev = sorted(transkun_notes, key=lambda x: -x[0])

    for note in transkun_notes_sorted_rev:
        current_time = note[0]
        if current_time < first_aligned_time:
            break
        group = [n for n in transkun_notes if abs(n[0] - current_time) < epsilon]
        group_pitches = [n[2] for n in group]
        match_count = sum(1 for p in gt_last_pitches if p in group_pitches)
        match_ratio = match_count / len(gt_last_pitches)
        if match_ratio >= 0.8:
            last_aligned_time = current_time
            print(f"[Last Anchor Match] Transkun time = {current_time:.3f}, Pitches at this time = {group_pitches}")
            break

    if last_aligned_time is None:
        raise RuntimeError("Failed to find matching last anchor in Transkun MIDI.")

    # === Linear Fit
    t0_gt = first_gt_time
    t1_gt = last_gt_time
    t0_aligned = first_aligned_time
    t1_aligned = last_aligned_time

    a = (t1_aligned - t0_aligned) / (t1_gt - t0_gt)
    b = t0_aligned - a * t0_gt
    print(f"[Linear Fit] t_aligned = {a:.6f} * t_gt + {b:.6f}")

    # === Apply
    for inst in gt_midi.instruments:
        for note in inst.notes:
            note.start = a * note.start + b
            note.end = a * note.end + b

    # === Write result
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gt_midi.write(str(output_path))
    print(f"Saved aligned GT MIDI to: {output_path}")

# ==== Main CLI ====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Align GT MIDI to Transkun MIDI by linear anchor fitting.")
    parser.add_argument("--gt", type=str, required=True, help="Path to original GT MIDI file")
    parser.add_argument("--transkun", type=str, required=True, help="Path to transkun MIDI file")
    parser.add_argument("--output", type=str, required=True, help="Path to save aligned GT MIDI")
    parser.add_argument("--epsilon", type=float, default=0.01, help="Time tolerance for anchor grouping (default: 0.01s)")
    args = parser.parse_args()

    align_gt_to_transkun(args.gt, args.transkun, args.output, epsilon=args.epsilon)
