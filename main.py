import argparse
import shutil
import sys
from pathlib import Path

import yt_dlp
from faster_whisper import WhisperModel

SENTENCE_END = tuple(".?!。？！…")
CJK_LANGS = {"zh", "ja", "ko", "yue"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download a video and generate a same-named SRT subtitle file with faster-whisper"
    )
    parser.add_argument("url", help="Video URL")
    parser.add_argument(
        "-o", "--output-dir", default=".",
        help="Directory for the video and subtitles (default: current directory; created if missing)",
    )
    parser.add_argument(
        "-m", "--model", default="small",
        help="Whisper model: tiny / base / small / medium / large-v3, etc. (default: small)",
    )
    parser.add_argument(
        "-l", "--language", default=None,
        help="Video language code, e.g. en, ja; auto-detected if omitted",
    )
    parser.add_argument(
        "--max-line", type=int, default=None,
        help="Max characters per subtitle line (default: 20 for CJK, 42 otherwise); at most two lines per cue",
    )
    return parser.parse_args()


def download(url: str, output_dir: Path) -> Path:
    opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mkv",
        "paths": {"home": str(output_dir)},
        "outtmpl": "%(title).80s [%(id)s].%(ext)s",
        "concurrent_fragment_downloads": 8,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(info["requested_downloads"][0]["filepath"])


def format_timestamp(seconds: float) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{s:06.3f}".replace(".", ",")


def wrap(text: str, max_line: int, cjk: bool) -> str:
    """超过一行长度时，在靠近中间的位置折成两行。"""
    if len(text) <= max_line:
        return text
    mid = len(text) // 2
    if cjk:
        # 优先在中间附近的标点后折行，找不到就直接从中间切
        for offset in range(0, mid):
            for i in (mid + offset, mid - offset):
                if 0 < i < len(text) and text[i - 1] in "，、,；;":
                    return text[:i] + "\n" + text[i:]
        return text[:mid] + "\n" + text[mid:]
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    if not spaces:
        return text
    cut = min(spaces, key=lambda i: abs(i - mid))
    return text[:cut] + "\n" + text[cut + 1:]


def make_cue(words, max_line, cjk):
    text = "".join(w.word for w in words).strip()
    return words[0].start, words[-1].end, wrap(text, max_line, cjk)


def build_cues(segments, language, max_line=None, max_duration=6.0, max_gap=1.0):
    """把 Whisper 的长段落按词级时间戳重新切成适合屏幕显示的短字幕。"""
    cjk = language in CJK_LANGS
    max_line = max_line or (20 if cjk else 42)
    max_chars = max_line * 2  # 每条字幕最多两行

    for seg in segments:
        words = []
        for w in seg.words or []:
            if words:
                text_len = len("".join(x.word for x in words).strip() + w.word)
                if (
                    text_len > max_chars                         # 太长
                    or w.end - words[0].start > max_duration     # 显示太久
                    or w.start - words[-1].end > max_gap         # 中间有停顿
                    or words[-1].word.strip().endswith(SENTENCE_END)  # 上一句已结束
                ):
                    yield make_cue(words, max_line, cjk)
                    words = []
            words.append(w)
        if words:
            yield make_cue(words, max_line, cjk)


def transcribe(video_path: Path, model_name: str, language: str | None,
               max_line: int | None) -> Path:
    print(f"\nLoading model {model_name} ...")
    model = WhisperModel(model_name, device="auto", compute_type="int8")

    segments, info = model.transcribe(
        str(video_path), language=language, vad_filter=True, word_timestamps=True
    )
    print(f"Detected language: {info.language} (confidence {info.language_probability:.2f})")
    print("Transcribing ...")

    srt_path = video_path.with_suffix(".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        cues = build_cues(segments, info.language, max_line)
        for i, (start, end, text) in enumerate(cues, 1):
            start_ts, end_ts = format_timestamp(start), format_timestamp(end)
            f.write(f"{i}\n{start_ts} --> {end_ts}\n{text}\n\n")
            print(f"[{start_ts} --> {end_ts}] {text.replace(chr(10), ' / ')}")
    return srt_path


def main():
    args = parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        print("Warning: ffmpeg not found; HD video and audio may fail to merge. "
              "Mac: brew install ffmpeg; Windows: winget install ffmpeg")

    try:
        video_path = download(args.url, output_dir)
    except yt_dlp.utils.DownloadError as e:
        print(f"Download failed: {e}")
        sys.exit(1)

    print(f"\nVideo saved: {video_path}")
    srt_path = transcribe(video_path, args.model, args.language, args.max_line)
    print(f"\nSubtitles saved: {srt_path}")
    print("Open the video in VLC to load the same-named subtitles automatically.")


if __name__ == "__main__":
    main()