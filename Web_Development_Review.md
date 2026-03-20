# Web Development Review (Detailed Code Walkthrough)

## Objective in This Project
The web layer provides a live assistive dashboard where users start detection, stream camera frames, and receive real-time object info, distance telemetry, and spoken/text navigation guidance.

## Where Web Logic Lives
- `flask_app.py`: Flask routes, Socket.IO events, detection lifecycle, integration with CV/IoT/GenAI.
- `templates/index.html`: Full frontend UI, event listeners, browser camera capture, rendering, audio playback.
- `Dockerfile` and `docker-compose.yml`: Runtime packaging and service startup.

## Backend Execution Flow (Flask + Socket.IO)
1. Startup:
- Tries to enable `eventlet.monkey_patch()`; falls back to `threading` mode when unavailable.
- Creates Flask app and Socket.IO server with CORS enabled.
- Optionally initializes AI crew (if imports + API key stack load correctly).

2. Route rendering:
- `@app.route('/')` serves `index.html`.
- `@app.route('/video_feed')` provides MJPEG stream using generator `generate_frames()`.

3. Detection lifecycle events:
- `start_detection` event sets `running=True` and emits status.
- Starts Arduino background thread if not already alive.
- Triggers immediate first instruction generation in background.
- `stop_detection` event sets `running=False` and emits stop status.

4. Frame ingestion modes:
- Server-camera mode (`generate_frames()`): opens `VIDEO_SOURCE`, reads OpenCV frames, calls `detect_objects`.
- Browser-camera mode (`client_frame`): decodes base64 JPEG from frontend canvas and runs `detect_objects`.
- Both modes emit `detected_objects` payload to UI.

5. Instruction scheduling:
- Global timing fields (`instruction_interval`, `next_instruction_ready_at`, `is_generating_instruction`) prevent instruction spam.
- When timer allows, `socketio.start_background_task(get_instructions, detected)` is launched.

## Critical Global State in `flask_app.py`
- `running`: Master switch for whether frame processing should produce detections.
- `camera`: OpenCV capture object opened lazily in `generate_frames()`.
- `last_detected_objects`: Shared cache used for immediate first instruction when user presses Start.
- `instruction_interval`: Seconds between instruction generations (currently 15.0).
- `next_instruction_ready_at`: Absolute timestamp gate for next AI instruction.
- `is_generating_instruction`: Mutex-like flag to avoid concurrent instruction threads.
- `arduino_running`, `arduino_thread`, `last_distance`: IoT thread state.

## Socket Event Contracts (Actual Payload Shapes)
- `status` from backend:
- `{"running": true|false, "message": "..."}`

- `detected_objects` from backend:
- `{"objects": [{"name": "chair", "confidence": 0.88, "direction": "moving away", "position": "left side"}]}`

- `navigation_instruction` from backend:
- `{"instruction": "...", "timestamp": "HH:MM:SS", "audio": "<base64 optional>"}`

- `distance_data` from backend:
- `{"distance": 43.2, "timestamp": "HH:MM:SS", "beep": true|false}`

- `arduino_status` from backend:
- `{"connected": true|false, "message": "Connected/Reconnecting/..."}`

## Frontend Runtime Flow (`templates/index.html`)
1. Socket bootstrap:
- Connects with `io()` and subscribes to events: `status`, `detected_objects`, `navigation_instruction`, `distance_data`, `arduino_status`.

2. Start button (`startDetection()`):
- Requests camera permission with `getUserMedia`.
- Binds stream to `<video id="localVideo">`.
- Starts frame loop at ~5 FPS.
- Sends each frame as JPEG base64 through `socket.emit('client_frame', { image })`.
- Emits `start_detection` to backend.

3. Stop button (`stopDetection()`):
- Stops frame interval timer.
- Stops local media tracks.
- Emits `stop_detection`.

4. Live UI updates:
- `detected_objects`: fills object list and confidence values.
- `distance_data`: updates cm reading, status time, and risk color (red/orange/blue).
- `navigation_instruction`: updates instruction text and plays audio if attached.
- If no backend audio, fallback browser speech synthesis is used.

## Browser Frame Pipeline (Exact Runtime Behavior)
1. `startFrameLoop()` creates an off-screen `<canvas>` and executes every `~200ms` (`targetFps=5`).
2. Each loop:
- Reads latest frame from `<video id="localVideo">`.
- Resizes to max width 640 to reduce bandwidth.
- Encodes JPEG with quality `0.6`.
- Sends data URL to backend via `socket.emit('client_frame', { image: dataUrl })`.
3. Backend receives event in `handle_client_frame(data)`:
- Strips `data:image/...;base64,` prefix.
- Decodes bytes with `base64.b64decode`.
- Converts bytes to numpy buffer and then OpenCV frame.
- Runs `detect_objects(frame)` and emits normalized result list.

## End-to-End Request Timeline (Start Button)
1. User clicks Start.
2. Frontend unlocks audio context and requests camera permission.
3. Frontend starts frame loop and emits `start_detection`.
4. Backend sets `running=True`, starts Arduino loop, emits `status`.
5. Frame events begin arriving at backend every ~200ms.
6. CV detections are emitted continuously as `detected_objects`.
7. Instruction scheduler periodically triggers `get_instructions(...)`.
8. Frontend updates instruction panel and plays server audio or TTS fallback.

## Deployment Behavior
- `Dockerfile` builds on `python:3.11-slim`, installs OpenCV/FFmpeg system libs, Python dependencies, exposes port 5000, and runs `python flask_app.py`.
- `docker-compose.yml` maps `5000:5000` and injects `OPENAI_API_KEY` and `VIDEO_SOURCE`.

## Strengths in Current Web Implementation
- Real-time event architecture (Socket.IO) avoids polling and reduces latency.
- Unified UI panel presents CV + IoT + AI outputs in one place.
- Browser camera path increases compatibility on platforms where direct camera passthrough is difficult in containers.
- Status events keep Start/Stop controls synchronized with backend state.

## Technical Risks / Review Notes
- Frontend is monolithic inline HTML/CSS/JS, harder to maintain as features grow.
- No authentication and no request/session protection for internet-facing deployment.
- `docker-compose.yml` currently has a malformed line under `environment` that looks like a device mapping string.
- Limited explicit UI feedback for backend failures (for example, model load failure).

## What to Say in the Review Demo
- "The browser captures frames, compresses them, and sends them over Socket.IO for backend inference."
- "The same event channel returns detected objects, distance data, and generated instructions in real time."
- "The UI supports both server-provided audio and browser fallback TTS, improving resilience."

## Suggested Engineering Upgrades
- Split frontend into modular assets (`static/js`, `static/css`) and componentize UI sections.
- Add auth + rate limiting + secure secrets strategy for production.
- Add Socket.IO integration tests for event contracts.
- Add a backend health endpoint and richer user-visible error banners.
