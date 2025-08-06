import pretty_midi
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from matplotlib.lines import Line2D

# ======== Parameters ========
start_time = 70        # start time
end_time = 80          # end time
tolerance = 0.01       #

# ======== Display Mode ========
display_mode = 'time'   # or frame
fps = 25                 # frame 25/1

# ======== File Paths ========
transkun_path = "/storage/user/ljia/folder_for_share/cam00045D6F85000_transcribed.mid"
aligned_path  = "/storage/user/ljia/folder_for_share/groundtruth_aligned_linear.mid"
output_png    = "/storage/user/ljia/folder_for_share/note_alignment_visualization_partial.png"

# ======== Load MIDI and Extract Notes ========
transkun_midi = pretty_midi.PrettyMIDI(transkun_path)
aligned_midi = pretty_midi.PrettyMIDI(aligned_path)

def filter_notes(notes, start, end):
    if start is None and end is None:
        return notes
    return [n for n in notes if (end is None or n[0] <= end) and (start is None or n[1] >= start)]

# Notes as (start, end, pitch)
gt_notes = [(n.start, n.end, n.pitch) for inst in transkun_midi.instruments for n in inst.notes]
pred_notes = [(n.start, n.end, n.pitch) for inst in aligned_midi.instruments for n in inst.notes]

gt_notes = filter_notes(gt_notes, start_time, end_time)
pred_notes = filter_notes(pred_notes, start_time, end_time)

# ======== Group notes by pitch ========
gt_by_pitch = defaultdict(list)
pred_by_pitch = defaultdict(list)

for s, e, p in gt_notes:
    gt_by_pitch[p].append((s, e))

for s, e, p in pred_notes:
    pred_by_pitch[p].append((s, e))

# ======== Overlap helper function ========
def has_overlap(s1, e1, s2, e2, tol):
    return max(0, min(e1, e2) - max(s1, s2)) > tol

# ======== Convert time to frame (or keep time) ========
def time2x(t):
    return t if display_mode == 'time' else t * fps

def label_xaxis():
    return "time (s)" if display_mode == 'time' else f"frame index (fps={fps})"

# ======== Compute segmented intervals ========
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

# ======== Plotting ========
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
        if start_time and e < start_time: continue
        if end_time and s > end_time: continue
        plt.plot([time2x(s), time2x(e)], [pitch, pitch], color=color, linewidth=2)

plt.xlabel(label_xaxis())
plt.ylabel("MIDI pitch")
plt.title("Partial Note-Level Overlap: Transkun vs Aligned GT MIDI")
plt.tight_layout()

if start_time is not None and end_time is not None:
    plt.xlim(time2x(start_time), time2x(end_time))

# Legend
legend_elements = [
    Line2D([0], [0], color='black', lw=2, label='transkun'),
    Line2D([0], [0], color='skyblue', lw=2, label='aligned GT'),
    Line2D([0], [0], color='red', lw=2, label='overlap'),
]
plt.legend(handles=legend_elements)

# Save and show
mode_str = "seconds" if display_mode == "time" else f"frames (fps={fps})"
plt.savefig(output_png, dpi=300)
print(f"Visualization saved to: {output_png} (x-axis in {mode_str})")
plt.show()
