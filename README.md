# transcript-generate-pipeline

Video subtitle transcription using yt-dlp and faster-whisper.

## Usage

Clone the project and install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/Cjantwhy/transcript-generate-pipeline.git
cd transcript-generate-pipeline
uv sync
```

Run it with a video URL, adjusting the options as needed:

```bash
uv run main.py <video-url> [-o OUTPUT_DIR] [-m MODEL] [-l LANGUAGE] [--max-line N] [-c N]
```

| Option | Description | Default |
| --- | --- | --- |
| `-o`, `--output-dir` | Directory for the video and subtitles | current directory |
| `-m`, `--model` | Whisper model (`tiny`, `base`, `small`, `medium`, `large-v3`, ...) | `small` |
| `-l`, `--language` | Language code, e.g. `en`, `ja` | auto-detect |
| `--max-line` | Max characters per subtitle line | 20 for CJK, 42 otherwise |
| `-c`, `--concurrent-fragments` | Number of fragments downloaded in parallel | `4` |

**About `-c`:** for long m3u8 (HLS) videos, which are split into many small fragments, raise this value (e.g. `8`); otherwise the download can be very slow. In other cases, start with a small value and increase it gradually if needed.

Example:

```bash
uv run main.py "https://www.youtube.com/watch?v=xxxx" -o videos -m medium -l en
```

## ffmpeg

Install [ffmpeg](https://ffmpeg.org/) if you want HD downloads, since the separate video and audio streams need to be merged:

- macOS: `brew install ffmpeg`
- Windows: `winget install ffmpeg`
