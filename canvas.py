import os
from pathlib import Path
import pretty_midi
import matplotlib.pyplot as plt


# ========= File paths (edit these) =========
PRED_PATH = "/storage/user/ljia/folder_for_share/case6/transkun_output.mid"
GT_PATH   = "/storage/user/ljia/folder_for_share/output.mid"

# ========= Anchors & window (edit these) =========
# Anchor times are in seconds on the (aligned) timeline.
# Add as many as you like.
anchor_times = [
    13.405,
120,240,
    360.0,480,
    600.0,720,
    900.0,
1500,
]
window = 10.0  # seconds before/after each anchor


# ========= Helper functions =========
def extract_notes(mid_path, time_range=None):
    """
    Extract (start, end, pitch) tuples from a MIDI file.
    If `time_range=(t0, t1)` is provided, only notes whose *start* lies within [t0, t1] are returned.
    """
    midi = pretty_midi.PrettyMIDI(str(mid_path))
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


def plot_notes(notes, ax, title, color="black"):
    """
    Plot notes as horizontal line segments on a simple piano-roll style axis.
    Each line goes from note onset to offset at the note's pitch.
    """
    for start, end, pitch in notes:
        ax.plot([start, end], [pitch, pitch], color=color, linewidth=2)
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("MIDI pitch")
    ax.set_ylim(20, 100)  # adjust if your range is wider/narrower
    ax.grid(True)


def main():
    # Basic existence checks
    if not Path(GT_PATH).exists():
        raise FileNotFoundError(f"GT MIDI not found: {GT_PATH}")
    if not Path(PRED_PATH).exists():
        raise FileNotFoundError(f"Pred MIDI not found: {PRED_PATH}")

    # Loop over anchors and generate one figure per anchor
    for idx, center_time in enumerate(anchor_times, start=1):
        t0 = center_time - window
        t1 = center_time + window

        # Extract notes in the time window for both files
        gt_notes   = extract_notes(GT_PATH, (t0, t1))
        pred_notes = extract_notes(PRED_PATH, (t0, t1))  # assuming timelines are aligned

        # Create a 2-row figure (GT on top, Transkun below)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
        plot_notes(gt_notes,   ax1, f"GT  ({t0:.3f}_{t1:.3f}s)",   color="green")
        plot_notes(pred_notes, ax2, f"Pred ({t0:.3f}_{t1:.3f}s)", color="red")
        plt.tight_layout()

        # Save with a descriptive filename
        out_name = f"midi_compare_anchor_{idx}_{center_time:.3f}s.png"
        plt.savefig(out_name, dpi=300)
        plt.close(fig)
        print(f"Saved: {out_name}")


if __name__ == "__main__":
    main()