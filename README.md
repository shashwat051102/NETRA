# Navigation Assistant (Flask + YOLOv8 + CrewAI)

This project streams camera video, performs YOLOv8 detection, generates navigation instructions via CrewAI (OpenAI), and sends synchronized text + audio to the browser via Flask‑SocketIO.

## Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- An OpenAI API key: set `OPENAI_API_KEY`
- For local webcam inside Docker:
  - Linux: `/dev/video0` can be passed into the container (see compose below)
  - Windows/macOS: direct host webcam passthrough to Linux containers is not reliable. Use an IP camera / RTSP app on phone as `VIDEO_SOURCE` (e.g., `rtsp://...`) or run without Docker.

## Build and Run with Docker Compose
Create a `.env` file next to `docker-compose.yml`:

```
OPENAI_API_KEY=sk-...yourkey...
```

Then build and run:

```
docker compose build
docker compose up
```

The app runs at http://localhost:5000

### Linux webcam mapping
Uncomment the `devices` section in `docker-compose.yml`:

```
services:
  app:
    devices:
      - "/dev/video0:/dev/video0"
```

### Configure video source
By default `VIDEO_SOURCE=0` (first camera). You can set:
- A different index: `VIDEO_SOURCE=1`
- A file path: `VIDEO_SOURCE=/app/sample.mp4` (mount/ copy file)
- A network stream: `VIDEO_SOURCE=rtsp://...` or `http://...`

## Manual Docker build/run
```
docker build -t nav-assistant:latest .
docker run --rm -p 5000:5000 ^
  -e OPENAI_API_KEY=%OPENAI_API_KEY% ^
  -e VIDEO_SOURCE=0 ^
  nav-assistant:latest
```
On Linux with webcam:
```
docker run --rm -p 5000:5000 \
  --device /dev/video0:/dev/video0 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e VIDEO_SOURCE=0 \
  nav-assistant:latest
```

## Notes
- The `Config/` directory paths were fixed for Linux case sensitivity.
- If Torch/Ultralytics installs slowly, it’s normal; the image includes `python:3.11-slim` with the required system libs for OpenCV/ffmpeg.
- If you see camera open errors in Docker on Windows/macOS, try setting `VIDEO_SOURCE` to an RTSP stream or run natively without Docker.
