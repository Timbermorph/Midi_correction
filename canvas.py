import pretty_midi
import matplotlib.pyplot as plt

def extract_notes(mid_path, time_range=None):
    """
    Extract note tuples (start, end, pitch) from a MIDI file.
    If time_range = (start, end), only notes within this range are included.
    If time_range = None, return all notes.
    """
    midi = pretty_midi.PrettyMIDI(mid_path)
    notes = []
    for inst in midi.instruments:
        if inst.is_drum:
            continue  # skip drum tracks
        for n in inst.notes:
            if time_range is None:
                notes.append((n.start, n.end, n.pitch))
            else:
                t0, t1 = time_range
                if t0 <= n.start <= t1:
                    notes.append((n.start, n.end, n.pitch))
    return notes

def plot_notes(notes, ax, label, color='black'):
    """
    Plot notes as horizontal lines on the piano roll.
    Each line represents a note from onset to offset.
    """
    for start, end, pitch in notes:
        ax.plot([start, end], [pitch, pitch], color=color, linewidth=2)
    ax.set_title(label)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('MIDI pitch')
    ax.set_ylim(20, 100)  # typical piano pitch range
    ax.grid(True)

# ========== File paths ==========
pred_path = "/storage/user/ljia/folder_for_share/case6/transkun_output.mid"
gt_path   = "/storage/user/ljia/folder_for_share/output.mid"

# ========== Time settings ==========
# Set to None to use full length, or specify a range like (0, 30)
gt_time_range   = (480, 500)  # or e.g. (0, 20)
pred_time_range = (480, 500)  # or e.g. (0, 20)

# ========== Extract notes ==========
gt_notes   = extract_notes(gt_path, gt_time_range)
pred_notes = extract_notes(pred_path, pred_time_range)

# ========== Plot both tracks ==========
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
plot_notes(gt_notes, ax1, "Ground Truth MIDI", color='green')
plot_notes(pred_notes, ax2, "Transkun Output MIDI", color='red')
plt.tight_layout()

# ========== Save the figure ==========
output_img = "midi_compare_segment.png"
plt.savefig(output_img, dpi=300)
print(f"Saved: {output_img}")
