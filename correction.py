import argparse
from pathlib import Path
import pretty_midi

# ==== Config ====
segment_minutes = 2
n_attempts = 5

# thresholds
THRESH_FIRST  = 0.80
THRESH_MIDDLE = 0.50
THRESH_LAST   = 0.80

# sequence params (middle anchors)
seq_len       = 5      # total groups to compare after sliding
seq_max_span  = 10     # seconds to collect the sequence groups

# monotonicity / numerics
safety_forward = 0.25  # enforce strictly increasing trans times
min_denom      = 1e-6  # avoid divide-by-zero

# expected-offset ? window scaling (you can tune these)
scale_back = 0.6       # back window = clamp(min_back,  scale_back * O_exp, max_back)
scale_fwd  = 1.4       # fwd  window = clamp(min_fwd,   scale_fwd  * O_exp, max_fwd)
min_back   = 0.5
max_back   = 10.0
min_fwd    = 5.0
max_fwd    = 25.0

# how many extra candidates to print after first middle-anchor match
extra_print_after = 5

# max sliding for GT/Trans sequences (prefix groups to allow skipping)
max_skip_prefix = 2

# ========== helpers ==========
def extract_notes(midi_path):
    """Return (notes, midi) where notes are (start, end, pitch) for non-drum."""
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    notes = []
    for inst in midi.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            notes.append((n.start, n.end, n.pitch))
    return notes, midi

def group_at_time(notes, t, epsilon):
    """All pitches whose onset is within epsilon of time t."""
    return [p for s, e, p in notes if abs(s - t) < epsilon]

def collect_gt_groups_from_time(gt_notes, start_time, epsilon, max_groups):
    """
    Collect up to `max_groups` GT pitch groups starting at or after `start_time`.
    A group is defined by the set of pitches at a distinct onset time.
    """
    groups, seen = [], set()
    for s, e, p in sorted(gt_notes, key=lambda x: x[0]):
        t = s
        if t < start_time - epsilon:
            continue
        if all(abs(t - st) >= epsilon for st in seen):
            groups.append((t, group_at_time(gt_notes, t, epsilon)))
            seen.add(t)
        if len(groups) >= max_groups:
            break
    return groups

def collect_group_sequence(notes, start_time, epsilon, max_groups, max_span):
    """
    Build a forward sequence of up to `max_groups` groups starting from the first
    onset >= start_time - epsilon, stopping if time span exceeds `max_span`.
    Returns: list[(t, [pitches])]
    """
    onset_times = sorted({s for s,_,_ in notes})
    i = 0
    while i < len(onset_times) and onset_times[i] < start_time - epsilon:
        i += 1
    seq, first_t = [], None
    while i < len(onset_times) and len(seq) < max_groups:
        t = onset_times[i]
        if first_t is None:
            first_t = t
        if (t - first_t) > max_span:
            break
        g = group_at_time(notes, t, epsilon)
        if g:
            seq.append((t, g))
        i += 1
    return seq

def group_match_ratio(gt_group, tr_group):
    """|intersection| / |gt_group|; 0 if gt_group empty."""
    if not gt_group:
        return 0.0
    inter = sum(1 for p in gt_group if p in tr_group)
    return inter / len(gt_group)

def clamp(lo, x, hi):
    return max(lo, min(x, hi))

# ========== your ORIGINAL first/last anchors ==========
def find_first_anchor_original(gt_notes, transkun_notes, epsilon, n_attempts):
    """Keep your original first-anchor search flow, threshold raised to 0.8."""
    gt_time_pitch_groups, seen = [], set()
    for note in sorted(gt_notes, key=lambda x: x[0]):
        t = note[0]
        if all(abs(t - st) >= epsilon for st in seen):
            gt_time_pitch_groups.append((t, group_at_time(gt_notes, t, epsilon)))
            seen.add(t)
        if len(gt_time_pitch_groups) >= n_attempts:
            break

    trans_sorted = sorted(transkun_notes, key=lambda x: x[0])
    best = None

    print("\n===== GT PITCH GROUPS (Top N) =====")
    for i, (t_gt, gt_group) in enumerate(gt_time_pitch_groups):
        print(f"Group {i+1}: Time = {t_gt:.3f}, GT Pitches = {sorted(gt_group)}")
        matched = False
        for s, e, p in trans_sorted:
            t_trans = s
            tr_group = group_at_time(transkun_notes, t_trans, epsilon)
            if not gt_group:
                continue
            ratio = group_match_ratio(gt_group, tr_group)
            if ratio >= THRESH_FIRST:
                print(f"Matched in Transkun at {t_trans:.3f}, Pitches = {sorted(tr_group)}, Match Ratio = {ratio:.2f}")
                matched = True
                if best is None or t_trans < best[2]:
                    best = (t_gt, gt_group, t_trans, i+1, ratio, tr_group)
                break  # only first match for each group
        if not matched:
            print("No match found in Transkun.")

    if best is None:
        raise RuntimeError("Failed to find matching first anchor in Transkun MIDI.")

    t_gt, gt_p, t_tr, idx, r, tr_p = best
    print("\n===== SELECTED FIRST ANCHOR =====")
    print(f"Selected Group: #{idx}")
    print(f"GT Time        : {t_gt:.3f}")
    print(f"GT Pitches     : {sorted(gt_p)}")
    print(f"Matched Time   : {t_tr:.3f} (in Transkun)")
    print(f"Matched Pitches: {sorted(tr_p)}")
    print(f"Match Ratio    : {r:.2f}")
    return best

def find_last_anchor_original(gt_notes, transkun_notes, epsilon, first_aligned_time):
    """Keep your original last-anchor search flow, threshold 0.8."""
    last_gt_time = max(n[0] for n in gt_notes)
    gt_last_pitches = [pitch for start, end, pitch in gt_notes if abs(start - last_gt_time) < epsilon]
    print(f"[GT Last Anchor] Time = {last_gt_time:.3f}, Pitches = {gt_last_pitches}")

    trans_sorted_rev = sorted(transkun_notes, key=lambda x: -x[0])
    last_aligned_time = None
    for s, e, p in trans_sorted_rev:
        current_time = s
        if current_time < first_aligned_time:
            break
        tr_group = group_at_time(transkun_notes, current_time, epsilon)
        if not gt_last_pitches:
            continue
        ratio = group_match_ratio(gt_last_pitches, tr_group)
        if ratio >= THRESH_LAST:
            last_aligned_time = current_time
            print(f"[Last Anchor Match] Transkun time = {current_time:.3f}, Pitches at this time = {tr_group}")
            break
    if last_aligned_time is None:
        raise RuntimeError("Failed to find matching last anchor in Transkun MIDI.")
    return (last_gt_time, gt_last_pitches, last_aligned_time, None, 1.0, gt_last_pitches)

# ========== bi-directional sliding sequence match ==========
def sequences_match_with_bi_sliding(
    gt_seq, tr_seq,
    per_group_thresh,
    seq_len=5,
    max_skip_gt=2,
    max_skip_tr=2,
):
    """
    Try all (skip_gt, skip_tr) pairs within [0, max_skip_*] and compare exactly `seq_len` groups:
        gt window = gt_seq[skip_gt : skip_gt + seq_len]
        tr window = tr_seq[skip_tr : skip_tr + seq_len]
    Each group's |n|/|GT| must be >= per_group_thresh.
    Returns: (ok, skip_gt, skip_tr, ratios[list of length seq_len])
    """
    if len(gt_seq) < 1 or len(tr_seq) < 1:
        return False, -1, -1, []

    for skip_gt in range(0, max_skip_gt + 1):
        if len(gt_seq) < skip_gt + seq_len:
            continue
        for skip_tr in range(0, max_skip_tr + 1):
            if len(tr_seq) < skip_tr + seq_len:
                continue

            ratios = []
            ok = True
            for (_, g_gt), (_, g_tr) in zip(
                gt_seq[skip_gt : skip_gt + seq_len],
                tr_seq[skip_tr : skip_tr + seq_len]
            ):
                if not g_gt:
                    ok = False
                    break
                inter = sum(1 for p in g_gt if p in g_tr)
                r = inter / len(g_gt)
                ratios.append(r)
                if r < per_group_thresh:
                    ok = False
                    break
            if ok:
                return True, skip_gt, skip_tr, ratios

    return False, -1, -1, []

# ========== middle anchors: expected-offset windows + bi-sliding sequence ==========
def find_segment_anchor_sequence_expected(
    gt_notes, transkun_notes,
    seg_start_gt_time, epsilon,
    center, back, fwd,
    prev_trans_time
):
    """
    For this segment start:
      - Build GT top-N groups; for each, collect a GT sequence with extra groups (for sliding).
      - Search Transkun times only in [lower_bound, upper_bound], where:
            lower_bound = max(center - back, prev_trans_time + safety_forward)
            upper_bound = center + fwd
      - For each candidate time:
            collect TR sequence with extra groups; run bi-directional sliding comparison
            (fixed seq_len, both sides can skip up to `max_skip_prefix`).
      - First valid match wins; also print up to `extra_print_after` later valid candidates.
      - Anchor times use the *slid* positions (gt_seq[skip_gt].time, tr_seq[skip_tr].time).
    """
    gt_groups = collect_gt_groups_from_time(gt_notes, seg_start_gt_time, epsilon, n_attempts)
    trans_times = sorted({s for s, _, _ in transkun_notes})

    # forward-only with small backward allowance + monotonic constraint
    lower_bound = center - back
    if prev_trans_time is not None:
        lower_bound = max(lower_bound, prev_trans_time + safety_forward)
    upper_bound = center + fwd

    print(f"\n===== [Segment start @ {seg_start_gt_time:.3f}s] GT PITCH GROUPS (Top N) =====")
    print(f"[Search window] Transkun: [{lower_bound:.3f}, {upper_bound:.3f}] (center={center:.3f}, back={back:.2f}, fwd={fwd:.2f})")

    for i, (t_gt, gt_group) in enumerate(gt_groups):
        print(f"Group {i+1}: Time = {t_gt:.3f}, GT Pitches = {sorted(gt_group)}")

        # Prepare GT sequence with extra groups for sliding
        gt_seq = collect_group_sequence(
            gt_notes, t_gt, epsilon,
            max_groups=seq_len + max_skip_prefix,  # allow skipping while still comparing seq_len groups
            max_span=seq_max_span
        )
        if len(gt_seq) < seq_len:
            print("  Skipping: GT pattern too short for sequence matching.")
            continue

        first_valid = None
        extra = []

        # Scan trans candidates in window
        for t_trans in trans_times:
            if t_trans < lower_bound or t_trans > upper_bound:
                continue

            # Build TR sequence with extra groups for sliding
            tr_seq = collect_group_sequence(
                transkun_notes, t_trans, epsilon,
                max_groups=seq_len + max_skip_prefix,
                max_span=seq_max_span
            )
            if len(tr_seq) < seq_len:
                continue

            # Bi-directional sliding sequence match
            ok, skip_gt, skip_tr, ratios = sequences_match_with_bi_sliding(
                gt_seq, tr_seq,
                per_group_thresh=THRESH_MIDDLE,
                seq_len=seq_len,
                max_skip_gt=max_skip_prefix,
                max_skip_tr=max_skip_prefix
            )
            if ok:
                anchor_gt_time = gt_seq[skip_gt][0]
                anchor_tr_time = tr_seq[skip_tr][0]

                if first_valid is None:
                    print(
                        f"Matched (bi-slide gt={skip_gt}, tr={skip_tr}) at TR {anchor_tr_time:.3f}, "
                        f"per-group={['%.2f' % r for r in ratios]}"
                    )
                    compared_tr_groups = [g for _, g in tr_seq[skip_tr : skip_tr + seq_len]]
                    first_valid = (anchor_gt_time, gt_seq[skip_gt][1], anchor_tr_time, i+1, min(ratios), compared_tr_groups)
                elif len(extra) < extra_print_after:
                    extra.append((anchor_tr_time, skip_gt, skip_tr, ratios))

        if first_valid is not None:
            if extra:
                print(f"[Debug] Next sequence candidates (up to {extra_print_after}):")
                for t_c, sgt, str_, rs in extra:
                    print(f"  - @ TR {t_c:.3f}, skip_gt={sgt}, skip_tr={str_}, per-group={['%.2f'%r for r in rs]}")
            return first_valid

        print("No bi-sliding sequence-level match for this GT group within window.")
    return None

# ========== main ==========
def align_gt_to_transkun(gt_midi_path, transkun_midi_path, output_path, epsilon=0.01):
    print(f"Running alignment with epsilon = {epsilon}")
    gt_notes, gt_midi = extract_notes(gt_midi_path)
    transkun_notes, _ = extract_notes(transkun_midi_path)

    total_time = max(n[0] for n in gt_notes)
    segment_length = segment_minutes * 60.0

    # segments on GT
    if total_time <= segment_length:
        print("Song shorter than one segment, using single-segment alignment.")
        segments = [(0.0, total_time)]
    else:
        segments = []
        t = 0.0
        while t < total_time:
            segments.append((t, min(t + segment_length, total_time)))
            t += segment_length
        print(f"Total time: {total_time:.2f}s, segments: {len(segments)}")

    anchors = []

    # FIRST anchor (original)
    first_anchor = find_first_anchor_original(gt_notes, transkun_notes, epsilon, n_attempts)
    anchors.append(first_anchor)
    first_gt_time, _, first_trans_time, _, _, _ = first_anchor

    # LAST anchor (original) � we find it NOW to estimate end offset for expected model
    print("\n===== [Final] GT Last Anchor =====")
    last_anchor = find_last_anchor_original(gt_notes, transkun_notes, epsilon, first_trans_time)
    anchors.append(last_anchor)  # append; middles will be inserted before this

    last_gt_time, _, last_trans_time, *_ = last_anchor
    O_end = last_trans_time - last_gt_time  # positive if Transkun is slower (GT "faster")
    T_total = last_gt_time

    # Middle anchors (insert between first and last)
    prev_trans_time = first_trans_time
    for idx in range(1, len(segments)):
        seg_start, seg_end = segments[idx]

        # expected offset at this segment start
        frac = seg_start / T_total if T_total > 0 else 0.0
        O_exp = O_end * frac
        center = seg_start + O_exp

        # scale windows from O_exp
        back = clamp(min_back,  scale_back * abs(O_exp), max_back)
        fwd  = clamp(min_fwd,   scale_fwd  * abs(O_exp), max_fwd)

        seg_anchor = find_segment_anchor_sequence_expected(
            gt_notes, transkun_notes,
            seg_start_gt_time=seg_start,
            epsilon=epsilon,
            center=center,
            back=back,
            fwd=fwd,
            prev_trans_time=prev_trans_time
        )

        if seg_anchor is None:
            # one widening pass (only forward)
            print("[Info] No match; widening forward window once (keep back from expected).")
            seg_anchor = find_segment_anchor_sequence_expected(
                gt_notes, transkun_notes,
                seg_start_gt_time=seg_start,
                epsilon=epsilon,
                center=center,
                back=back,
                fwd=fwd * 1.5,
                prev_trans_time=prev_trans_time
            )
            if seg_anchor is None:
                raise RuntimeError(f"Failed to find anchor for segment starting at {seg_start:.3f}s")

        # insert this middle anchor before the last anchor
        anchors.insert(-1, seg_anchor)
        prev_trans_time = seg_anchor[2]

    # Build per-segment mappings from consecutive anchors
    mappings = []
    # anchors order: [first, seg1, seg2, ..., last]
    for i in range(len(segments)):
        t0_gt, _, t0_tr, *_ = anchors[i]
        t1_gt, _, t1_tr, *_ = anchors[i+1]
        denom = (t1_gt - t0_gt)
        if abs(denom) < min_denom:
            if mappings:
                a, b = mappings[-1][2], mappings[-1][3]
                print(f"\n[Segment {i+1}] degenerate anchor times; reusing previous mapping: a={a:.6f}, b={b:.6f}")
            else:
                a, b = 1.0, 0.0
                print(f"\n[Segment {i+1}] degenerate anchor times; using identity: a=1.000000, b=0.000000")
        else:
            a = (t1_tr - t0_tr) / denom
            b = t0_tr - a * t0_gt
            print(f"\n[Segment {i+1}] GT {segments[i][0]:.2f}-{segments[i][1]:.2f}s => Mapping: a={a:.6f}, b={b:.6f}")
        mappings.append((segments[i][0], segments[i][1], a, b))

    # Apply mapping
    for inst in gt_midi.instruments:
        for note in inst.notes:
            for seg_start, seg_end, a, b in mappings:
                if seg_start <= note.start < seg_end + epsilon:
                    note.start = a * note.start + b
                    note.end   = a * note.end   + b
                    break

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gt_midi.write(str(output_path))
    print(f"\nSaved aligned GT MIDI to: {output_path}")

# ==== CLI ====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Align GT MIDI to Transkun MIDI with expected-offset windows and bi-sliding sequence-based middle anchors (first/last original).")
    parser.add_argument("--gt", type=str, required=True, help="Path to original GT MIDI file")
    parser.add_argument("--transkun", type=str, required=True, help="Path to transkun MIDI file")
    parser.add_argument("--output", type=str, required=True, help="Path to save aligned GT MIDI")
    parser.add_argument("--epsilon", type=float, default=0.01, help="Time tolerance for grouping (default: 0.01s)")
    args = parser.parse_args()
    align_gt_to_transkun(args.gt, args.transkun, args.output, epsilon=args.epsilon)
