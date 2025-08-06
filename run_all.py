import os
import subprocess
from pathlib import Path
from tqdm import tqdm

# Paths
BASE_DIR = Path("/storage/user/ljia/folder_for_share")
SOURCE_DIR = BASE_DIR / "2025-07-18"
TRANSTOOL = "transkun"
FPS = 25

# Scripts (assumed in same folder or full path)
CORRECTION = "correction.py"
TOAUDIO = "toaudio.py"
OVERLAP = "overlap.py"

# Collect cases
subfolders = sorted([d for d in SOURCE_DIR.iterdir() if d.is_dir()])
total_cases = len(subfolders)
print(f"Found {total_cases} cases.")

# Process with tqdm progress bar
for idx, subdir in enumerate(tqdm(subfolders, desc="Processing Cases"), start=1):
    case_dir = BASE_DIR / f"case{idx}"
    case_dir.mkdir(exist_ok=True)
    
    video_path = subdir / "cam00045D6F85000.mp4"
    gt_midi_path = subdir / f"{subdir.name}.mid"
    extracted_mp3 = case_dir / "audio.mp3"
    transkun_midi = case_dir / "transkun_output.mid"
    aligned_midi = case_dir / "aligned_output.mid"
    audio_output_wav = case_dir / "aligned_output.wav"
    new_mp4_path = case_dir / "output_aligned.mp4"
    overlap_png = case_dir / "overlap.png"

    try:
        # Step 1: Extract audio
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-q:a", "0", "-map", "a", str(extracted_mp3)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Step 2: Run transkun
        subprocess.run([
            TRANSTOOL, str(extracted_mp3), str(transkun_midi)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Step 3: Align
        subprocess.run([
            "python", CORRECTION,
            "--gt", str(gt_midi_path),
            "--transkun", str(transkun_midi),
            "--output", str(aligned_midi)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Step 4: Synthesize audio
        subprocess.run([
            "python", TOAUDIO,
            "--midi", str(aligned_midi),
            "--output", str(audio_output_wav)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Step 5: Replace audio
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_output_wav),
            "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", str(new_mp4_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Step 6: Generate overlap visualization
        subprocess.run([
            "python", OVERLAP,
            "--transkun", str(transkun_midi),
            "--aligned", str(aligned_midi),
            "--output", str(overlap_png),
            "--start", "70", "--end", "80",
            "--display_mode", "time",
            "--fps", str(FPS)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    except subprocess.CalledProcessError:
        print(f"\nError processing case{idx}: {subdir.name}")
        continue

print("\nAll cases processed.")
