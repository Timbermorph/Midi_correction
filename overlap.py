import argparse
import pretty_midi
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from matplotlib.lines import Line2D
from pathlib import Path

def filter_notes(notes, start, end):
    if start is None and end is None:
        return notes
    return [n for n in notes if (end is None or n[0] <= end) and (start is None or n[1] >= start)]

def has_overlap(s1, e1, s2, e2, tol):
    return max(0, min(e1, e2) - max(s1, s2)) > tol

def split_segments(intervals_a, intervals_b, color_a, color_b, overlap_color, tol):
    all_times = []
    for s, e in intervals_a + intervals_b:
        all_times.extend([s, e])
    all_times = sorted(set(all_times))

    segments = []
    for i in range(len(all_times) - 1):
        seg_start = all_times[i]
        seg_end = all_times[i + 1]

        in_a = any(has_overlap(seg_start, seg_end, s, e, tol) for s, e in intervals_a)
        in_b = any(has_overlap(seg_start, seg_end, s, e, tol) for s, e in intervals_b)

        if in_a and in_b:
            color = overlap_color
        elif in_a:
            color = color_a
        elif in_b:
            color = color_b
        else:
            continue
        segments.append((seg_start, seg_end, color))
    return segments

def time2x(t, display_mode, fps):
    return t if display_mode == 'time' else t * fps

def label_xaxis(display_mode, fps):
    return "time (s)" if display_mode == 'time' else f"frame index (fps={fps})"

def plot_overlap(transkun_path, aligned_path, output_path, start_time, end_time, tolerance, display_mode, fps):
    transkun_midi = pretty_midi.PrettyMIDI(str(transkun_path))
    aligned_midi = pretty_midi.PrettyMIDI(str(aligned_path))

    gt_notes = [(n.start, n.end, n.pitch) for inst in transkun_midi.instruments for n in inst.notes]
    pred_notes = [(n.start, n.end, n.pitch) for inst in aligned_midi.instruments for n in inst.notes]

    gt_notes = filter_notes(gt_notes, start_time, end_time)
    pred_notes = filter_notes(pred_notes, start_time, end_time)

    gt_by_pitch = defaultdict(list)
    pred_by_pitch = defaultdict(list)
    for s, e, p in gt_notes:
        gt_by_pitch[p].append((s, e))
    for s, e, p in pred_notes:
        pred_by_pitch[p].append((s, e))

    plt.figure(figsize=(12, 6))

    all_pitches = sorted(set(gt_by_pitch.keys()).union(pred_by_pitch.keys()))
    for pitch in all_pitches:
        gt_intervals = gt_by_pitch.get(pitch, [])
        pred_intervals = pred_by_pitch.get(pitch, [])
        segments = split_segments(gt_intervals, pred_intervals,
                                  color_a='black',
                                  color_b='skyblue',
                                  overlap_color='red',
                                  tol=tolerance)
        for s, e, color in segments:
            if start_time and e < start_time:
                continue
            if end_time and s > end_time:
                continue
            plt.plot([time2x(s, display_mode, fps), time2x(e, display_mode, fps)], [pitch, pitch], color=color, linewidth=2)

    plt.xlabel(label_xaxis(display_mode, fps))
    plt.ylabel("MIDI pitch")
    plt.title("Partial Note-Level Overlap: Transkun vs Aligned GT MIDI")
    plt.tight_layout()

    if start_time is not None and end_time is not None:
        plt.xlim(time2x(start_time, display_mode, fps), time2x(end_time, display_mode, fps))

    legend_elements = [
        Line2D([0], [0], color='black', lw=2, label='transkun'),
        Line2D([0], [0], color='skyblue', lw=2, label='aligned GT'),
        Line2D([0], [0], color='red', lw=2, label='overlap'),
    ]
    plt.legend(handles=legend_elements)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    print(f"Visualization saved to: {output_path} (x-axis in {display_mode})")
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot note-level overlap between transkun and aligned GT MIDI.")
    parser.add_argument("--transkun", type=str, required=True, help="Path to transkun MIDI file")
    parser.add_argument("--aligned", type=str, required=True, help="Path to aligned GT MIDI file")
    parser.add_argument("--output", type=str, required=True, help="Path to save the overlap visualization image")
    parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds")
    parser.add_argument("--end", type=float, default=None, help="End time in seconds")
    parser.add_argument("--tolerance", type=float, default=0.01, help="Overlap tolerance in seconds")
    parser.add_argument("--display_mode", type=str, choices=["time", "frame"], default="frame", help="X-axis mode")
    parser.add_argument("--fps", type=int, default=25, help="FPS when using frame display mode")
    args = parser.parse_args()

    plot_overlap(args.transkun, args.aligned, args.output,
                 start_time=args.start,
                 end_time=args.end,
                 tolerance=args.tolerance,
                 display_mode=args.display_mode,
                 fps=args.fps)
