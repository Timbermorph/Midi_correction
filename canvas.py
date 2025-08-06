import pretty_midi
import matplotlib.pyplot as plt

def extract_notes(mid_path, max_time=None):
    """
    Extract note tuples (start, end, pitch) from a MIDI file.
    If max_time is specified, only notes before that time are included.
    """
    midi = pretty_midi.PrettyMIDI(mid_path)
    notes = []
    for inst in midi.instruments:
        if inst.is_drum:
            continue  # skip drum tracks
        for n in inst.notes:
            if max_time is None or n.start <= max_time:
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

# File paths for ground truth MIDI and predicted MIDI
# gt_path = "/storage/user/ljia/folder_for_share/2025-06-19/MIDI-Unprocessed_SMF_02_R1_2004_01-05_ORIG_MID--AUDIO_02_R1_2004_05_Track05_wav.midi/MIDI-Unprocessed_SMF_02_R1_2004_01-05_ORIG_MID--AUDIO_02_R1_2004_05_Track05_wav.midi"
gt_path = "/storage/user/ljia/folder_for_share/groundtruth_aligned_linear.mid"
pred_path = "/storage/user/ljia/folder_for_share/cam00045D6F85000_transcribed.mid"

# Extract notes from both files (use max_time=None for full duration)
gt_notes = extract_notes(gt_path, max_time=None)
pred_notes = extract_notes(pred_path, max_time=None)

# Plot both tracks for comparison
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
plot_notes(gt_notes, ax1, "Ground Truth MIDI", color='green')
plot_notes(pred_notes, ax2, "Transkun Output MIDI", color='red')
plt.tight_layout()

# Save the figure to the current directory
plt.savefig("midi_compare_10_whole.png", dpi=300)
print("Saved: midi_compare_10.png")
