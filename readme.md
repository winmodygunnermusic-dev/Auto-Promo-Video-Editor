# Auto Promo Video Editor (Tkinter + MoviePy 1.0.1)

A Windows-friendly Python desktop app that automatically creates short promo/remix/parody/song-montage videos from folders of clips, music, and sound effects.

## Features

- Tkinter GUI with:
  - Select video clips folder
  - Select audio/music folder
  - Select sound effects folder
  - Select output folder
  - Mode selector
  - Start Auto Edit button
  - Progress bar + live status log
- Fully automatic editing pipeline (no AI, no text overlays)
- MoviePy 1.0.1 + FFmpeg rendering
- Randomized clip trimming, shuffle, effects, and audio layering

## Modes

- **Auto Promo**
- **Auto Remix**
- **Auto Parody**
- **Auto Song Montage**

Each mode changes clip timing, effect intensity, looping chance, and audio behavior.

## Requirements

- Windows 8.1 (target platform)
- Python 3.x
- FFmpeg installed and available in `PATH`

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## Output Settings

- Format: MP4
- Video codec: `libx264`
- Audio codec: `aac`
- Resolution: 240p (height = 240)
- Bitrate: 100k
- Duration: randomly targeted between 30 and 60 seconds

## Project Structure

- `app.py` – GUI and full auto-edit pipeline
- `requirements.txt` – pinned runtime dependencies (`moviepy==1.0.1`)

