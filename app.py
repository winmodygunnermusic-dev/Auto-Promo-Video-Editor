import os
import random
import threading
import traceback
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.fx import all as vfx
from moviepy.audio.fx import all as afx

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".m4a", ".ogg"}


@dataclass
class ModeConfig:
    clip_len_range: Tuple[float, float]
    effect_probability: float
    loop_probability: float
    speed_range: Tuple[float, float]
    sfx_count_range: Tuple[int, int]
    beat_jitter: float


MODE_CONFIGS: Dict[str, ModeConfig] = {
    "Auto Promo": ModeConfig((2.0, 4.0), 0.55, 0.25, (0.85, 1.35), (4, 10), 0.22),
    "Auto Remix": ModeConfig((1.8, 3.8), 0.70, 0.35, (0.7, 1.65), (8, 18), 0.15),
    "Auto Parody": ModeConfig((2.5, 5.0), 0.85, 0.55, (0.55, 1.9), (10, 24), 0.30),
    "Auto Song Montage": ModeConfig((2.0, 4.5), 0.45, 0.20, (0.9, 1.2), (3, 8), 0.10),
}


class AutoPromoEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Auto Promo Video Editor")
        self.root.geometry("760x560")

        self.video_folder = tk.StringVar()
        self.music_folder = tk.StringVar()
        self.sfx_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.mode_var = tk.StringVar(value="Auto Promo")

        self._build_ui()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Video clips folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.video_folder, width=70).grid(row=0, column=1, padx=6)
        ttk.Button(frm, text="Select", command=lambda: self._pick_dir(self.video_folder)).grid(row=0, column=2)

        ttk.Label(frm, text="Audio/music folder:").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.music_folder, width=70).grid(row=1, column=1, padx=6)
        ttk.Button(frm, text="Select", command=lambda: self._pick_dir(self.music_folder)).grid(row=1, column=2)

        ttk.Label(frm, text="Sound effects folder:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.sfx_folder, width=70).grid(row=2, column=1, padx=6)
        ttk.Button(frm, text="Select", command=lambda: self._pick_dir(self.sfx_folder)).grid(row=2, column=2)

        ttk.Label(frm, text="Output folder:").grid(row=3, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.output_folder, width=70).grid(row=3, column=1, padx=6)
        ttk.Button(frm, text="Select", command=lambda: self._pick_dir(self.output_folder)).grid(row=3, column=2)

        ttk.Label(frm, text="Mode:").grid(row=4, column=0, sticky="w", pady=(8, 4))
        mode_combo = ttk.Combobox(frm, textvariable=self.mode_var, values=list(MODE_CONFIGS.keys()), state="readonly")
        mode_combo.grid(row=4, column=1, sticky="w", pady=(8, 4))

        self.start_btn = ttk.Button(frm, text="Start Auto Edit", command=self.start_auto_edit)
        self.start_btn.grid(row=5, column=1, sticky="w", pady=(8, 6))

        self.progress = ttk.Progressbar(frm, orient="horizontal", mode="determinate", length=520, maximum=100)
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 8))

        ttk.Label(frm, text="Status log:").grid(row=7, column=0, sticky="w")
        self.log_box = tk.Text(frm, height=20, width=92, state="disabled")
        self.log_box.grid(row=8, column=0, columnspan=3, sticky="nsew")

        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(8, weight=1)

    def _pick_dir(self, var: tk.StringVar) -> None:
        selected = filedialog.askdirectory()
        if selected:
            var.set(selected)

    def _log(self, message: str) -> None:
        def append() -> None:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.root.after(0, append)

    def _set_progress(self, value: float) -> None:
        self.root.after(0, lambda: self.progress.configure(value=max(0, min(100, value))))

    def start_auto_edit(self) -> None:
        fields = {
            "Video clips folder": self.video_folder.get(),
            "Audio/music folder": self.music_folder.get(),
            "Sound effects folder": self.sfx_folder.get(),
            "Output folder": self.output_folder.get(),
        }
        missing = [k for k, v in fields.items() if not v or not os.path.isdir(v)]
        if missing:
            messagebox.showerror("Missing folders", "Please select valid folders for:\n- " + "\n- ".join(missing))
            return

        self.start_btn.configure(state="disabled")
        self.progress.configure(value=0)
        self._log("Starting automatic edit...")
        worker = threading.Thread(target=self._run_pipeline, daemon=True)
        worker.start()

    def _run_pipeline(self) -> None:
        clips: List[VideoFileClip] = []
        music_clip: Optional[AudioFileClip] = None
        sfx_clips: List[AudioFileClip] = []
        final_video: Optional[VideoFileClip] = None
        try:
            mode_name = self.mode_var.get()
            config = MODE_CONFIGS[mode_name]
            target_duration = random.uniform(30.0, 60.0)
            self._log(f"Mode: {mode_name} | target duration: {target_duration:.1f}s")

            self._set_progress(5)
            clips = load_clips(self.video_folder.get(), config, target_duration, self._log)
            if not clips:
                raise RuntimeError("No video clips could be loaded from the selected folder.")

            self._set_progress(35)
            edited = [apply_random_effects(c, config, self._log) for c in clips]
            random.shuffle(edited)
            montage = concatenate_videoclips(edited, method="compose")

            self._set_progress(55)
            music_clip, sfx_clips, mixed_audio = mix_audio(
                montage.duration,
                self.music_folder.get(),
                self.sfx_folder.get(),
                config,
                self._log,
            )
            final_video = montage.set_audio(mixed_audio)

            self._set_progress(75)
            output_path = render_video(final_video, self.output_folder.get(), mode_name, self._log)

            self._set_progress(100)
            self._log(f"Done! Output: {output_path}")
            self.root.after(0, lambda: messagebox.showinfo("Finished", f"Video rendered:\n{output_path}"))
        except Exception as exc:
            self._log(f"ERROR: {exc}")
            self._log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Auto Edit Failed", str(exc)))
        finally:
            for c in clips:
                try:
                    c.close()
                except Exception:
                    pass
            if final_video:
                try:
                    final_video.close()
                except Exception:
                    pass
            if music_clip:
                try:
                    music_clip.close()
                except Exception:
                    pass
            for sfx in sfx_clips:
                try:
                    sfx.close()
                except Exception:
                    pass

            self.root.after(0, lambda: self.start_btn.configure(state="normal"))


def _list_media(folder: str, extensions: set) -> List[str]:
    files = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in extensions:
            files.append(path)
    return files


def load_clips(video_folder: str, config: ModeConfig, target_duration: float, logger) -> List[VideoFileClip]:
    video_paths = _list_media(video_folder, VIDEO_EXTS)
    if not video_paths:
        return []

    logger(f"Found {len(video_paths)} source clips.")
    assembled: List[VideoFileClip] = []
    total = 0.0
    safety = 0

    while total < target_duration and safety < 200:
        safety += 1
        src = random.choice(video_paths)
        base = VideoFileClip(src, audio=False)
        min_len, max_len = config.clip_len_range

        if base.duration <= 0.2:
            base.close()
            continue

        desired = random.uniform(min_len, max_len)
        trimmed_len = min(desired, max(0.2, base.duration))
        start_max = max(0.0, base.duration - trimmed_len)
        start = random.uniform(0, start_max) if start_max > 0 else 0.0

        clip = base.subclip(start, start + trimmed_len)
        base.close()

        if random.random() < config.loop_probability and clip.duration < max_len:
            loop_times = random.choice([2, 3])
            clip = clip.fx(vfx.loop, n=loop_times)
            logger(f"Looped clip x{loop_times}")

        assembled.append(clip)
        total += clip.duration

    logger(f"Built montage from {len(assembled)} randomized clip segments.")
    return assembled


def apply_random_effects(clip: VideoFileClip, config: ModeConfig, logger) -> VideoFileClip:
    fx_clip = clip

    if random.random() < config.effect_probability:
        flash_factor = random.uniform(1.15, 1.55)
        fx_clip = fx_clip.fx(vfx.colorx, flash_factor)

    if random.random() < (config.effect_probability * 0.6):
        fx_clip = fx_clip.fx(vfx.invert_colors)

    if random.random() < config.effect_probability:
        speed = random.uniform(*config.speed_range)
        speed = max(0.35, speed)
        fx_clip = fx_clip.fx(vfx.speedx, speed)

    if fx_clip.duration > 0.06:
        fx_clip = fx_clip.fx(vfx.fadein, min(0.08, fx_clip.duration / 4.0)).fx(
            vfx.fadeout, min(0.08, fx_clip.duration / 4.0)
        )

    logger(f"Applied effects; duration now {fx_clip.duration:.2f}s")
    return fx_clip


def _choose_beats(duration: float, bpm: float, jitter: float) -> List[float]:
    if bpm <= 0:
        return []
    beat = 60.0 / bpm
    t = 0.0
    times = []
    while t < duration:
        offset = random.uniform(-jitter, jitter)
        times.append(max(0.0, min(duration, t + offset)))
        t += beat
    return times


def mix_audio(total_duration: float, music_folder: str, sfx_folder: str, config: ModeConfig, logger):
    music_candidates = _list_media(music_folder, AUDIO_EXTS)
    if not music_candidates:
        raise RuntimeError("No audio/music files were found.")

    sfx_candidates = _list_media(sfx_folder, AUDIO_EXTS)
    if not sfx_candidates:
        logger("No SFX found; rendering with music only.")

    bg_music_path = random.choice(music_candidates)
    bg_music = AudioFileClip(bg_music_path)
    logger(f"Selected music: {os.path.basename(bg_music_path)}")

    if bg_music.duration < total_duration:
        loops = int(total_duration // bg_music.duration) + 1
        bg_music = bg_music.fx(afx.audio_loop, duration=total_duration)
        logger(f"Looped music x{loops}")
    else:
        start = random.uniform(0, max(0, bg_music.duration - total_duration))
        bg_music = bg_music.subclip(start, start + total_duration)

    bg_music = bg_music.volumex(0.65)

    bpm_guess = random.choice([90, 100, 110, 120, 128, 140])
    beat_points = _choose_beats(total_duration, bpm_guess, config.beat_jitter)
    logger(f"Using approximate beat grid at {bpm_guess} BPM.")

    layered = [bg_music]
    spawned_sfx: List[AudioFileClip] = []

    count_min, count_max = config.sfx_count_range
    sfx_to_add = random.randint(count_min, count_max) if sfx_candidates else 0

    for _ in range(sfx_to_add):
        path = random.choice(sfx_candidates)
        sfx = AudioFileClip(path)
        spawned_sfx.append(sfx)

        max_len = min(1.2, sfx.duration)
        if max_len <= 0:
            continue
        sfx_len = random.uniform(0.08, max_len)
        sfx_part = sfx.subclip(0, sfx_len).volumex(random.uniform(0.25, 0.90))

        if beat_points:
            t = random.choice(beat_points)
        else:
            t = random.uniform(0, max(0.0, total_duration - sfx_len))
        layered.append(sfx_part.set_start(t))

    mixed = CompositeAudioClip(layered).set_duration(total_duration)
    logger(f"Added {sfx_to_add} random SFX hits.")

    return bg_music, spawned_sfx, mixed


def render_video(video, output_folder: str, mode_name: str, logger) -> str:
    os.makedirs(output_folder, exist_ok=True)
    safe_mode = mode_name.replace(" ", "_").lower()
    filename = f"auto_{safe_mode}_{random.randint(1000, 9999)}.mp4"
    output_path = os.path.join(output_folder, filename)

    final = video.resize(height=240)
    logger("Rendering 240p MP4 at 100k bitrate...")
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        bitrate="100k",
        fps=24,
        preset="medium",
        threads=2,
        ffmpeg_params=["-movflags", "+faststart"],
    )
    final.close()
    return output_path


def main() -> None:
    root = tk.Tk()
    app = AutoPromoEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
