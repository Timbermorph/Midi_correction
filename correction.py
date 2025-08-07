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

    n_attempts = 5  # You can change this
    gt_time_pitch_groups = []
    seen_times = set()

    # Step 1: Extract top-N GT pitch groups
    for note in sorted(gt_notes, key=lambda x: x[0]):
        t = note[0]
        if all(abs(t - seen) >= epsilon for seen in seen_times):
            group = [pitch for s, e, pitch in gt_notes if abs(s - t) < epsilon]
            gt_time_pitch_groups.append((t, group))
            seen_times.add(t)
        if len(gt_time_pitch_groups) >= n_attempts:
            break

    transkun_notes_sorted = sorted(transkun_notes, key=lambda x: x[0])
    best_anchor = None  # (gt_time, group, trans_time)

    print("\n===== GT PITCH GROUPS (Top N) =====")
    for i, (t_gt, gt_group) in enumerate(gt_time_pitch_groups):
        print(f"Group {i+1}: Time = {t_gt:.3f}, GT Pitches = {sorted(gt_group)}")
        matched = False
        for note in transkun_notes_sorted:
            t_trans = note[0]
            group = [n for n in transkun_notes if abs(n[0] - t_trans) < epsilon]
            group_pitches = [n[2] for n in group]
            match_count = sum(1 for p in gt_group if p in group_pitches)
            match_ratio = match_count / len(gt_group)
            if match_ratio >= 0.4:
                print(f"Matched in Transkun at {t_trans:.3f}, Pitches = {sorted(group_pitches)}, Match Ratio = {match_ratio:.2f}")
                matched = True
                if best_anchor is None or t_trans < best_anchor[2]:
                    best_anchor = (t_gt, gt_group, t_trans, i+1, match_ratio, group_pitches)
                break  # only first match for each group
        if not matched:
            print(f"No match found in Transkun.")

    # Step 3: Choose best match
    if best_anchor is None:
        raise RuntimeError("Failed to find matching first anchor in Transkun MIDI.")

    first_gt_time, gt_first_pitches, first_aligned_time, group_idx, match_ratio, matched_pitches = best_anchor
    print("\n===== SELECTED FIRST ANCHOR =====")
    print(f"Selected Group: #{group_idx}")
    print(f"GT Time        : {first_gt_time:.3f}")
    print(f"GT Pitches     : {sorted(gt_first_pitches)}")
    print(f"Matched Time   : {first_aligned_time:.3f} (in Transkun)")
    print(f"Matched Pitches: {sorted(matched_pitches)}")
    print(f"Match Ratio    : {match_ratio:.2f}")

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
