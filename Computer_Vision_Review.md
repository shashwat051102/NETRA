# Computer Vision Review (Detailed Code Walkthrough)

## Objective in This Project
The computer vision layer detects surrounding objects from live video and enriches each detection with movement direction and scene position so the guidance layer can generate useful instructions for a visually impaired user.

## Where CV Logic Lives
- `Object_Detection/predict.py`: Model loading, inference, tracking update, frame annotation, output formatting.
- `Object_Detection/direction_tracker.py`: Temporal tracking and movement-direction interpretation.
- `flask_app.py`: Calls `detect_objects(...)` from camera streams and emits results to UI/AI modules.

## Runtime Flow (What Happens in Code)
1. Module load time (`Object_Detection/predict.py`):
- Selects compute device using `torch.cuda.is_available()`.
- Loads model file `Object_Detection/yolov8m.pt` into Ultralytics `YOLO`.
- Moves model to selected device.
- Creates a `DirectionTracker` instance with history size and movement threshold.

2. Frame processing (`detect_objects(frame, conf_threshold=0.5)`):
- Receives one BGR frame from OpenCV.
- Runs YOLO inference (`model(frame, conf=0.5, verbose=False)`).
- Iterates every predicted box to extract:
- Bounding coordinates `x1, y1, x2, y2`
- Confidence score
- Class id and class name from `model.names`
- Builds `detection_w_bbox` list for temporal tracker input.

3. Motion understanding:
- Sends detections to `direction_tracker.update(detection_w_bbox)`.
- Tracker compares current and previous observations of each object candidate.
- Returns enriched tuples including `direction` and distance trend.

4. Annotation and semantic packaging:
- Copies original frame to `annotated_frame`.
- Draws colored boxes (red for approaching, blue for moving away, green otherwise).
- Builds readable label text (`name`, `confidence`, and optional movement).
- Adds position description using `direction_tracker.get_position_description(...)`.
- Appends normalized tuple to `detected` output: `(name, conf, direction, position)`.

5. Return behavior:
- On success: returns `(detected, annotated_frame)`.
- On exception: prints traceback and returns `([], frame)` to keep pipeline alive.

## How CV Connects to the Rest of the App
- `flask_app.py:generate_frames()` reads server-side camera frames, calls `detect_objects(frame)`, and emits `detected_objects` to browser.
- `flask_app.py:handle_client_frame(...)` decodes browser JPEG base64 frames, runs same `detect_objects(...)`, and emits results.
- The same detection tuple is reused by the Gen AI stage (`get_instructions`) for natural-language guidance.

## Current Model and Inference Choices
- Model in use: `yolov8m.pt`.
- Inference threshold currently hardcoded as `conf=0.5` inside model call.
- Output is object-centric and optimized for real-time socket updates, not for archival evaluation datasets.

## Strengths in Current Implementation
- Single CV function serves both server camera and browser camera paths.
- Temporal direction tracking gives more practical navigation context than static labels.
- Defensive exception handling prevents one bad frame from crashing streaming.
- Annotated frame generation supports visual debugging during development.

## Technical Risks / Review Notes
- `conf_threshold` parameter exists but function uses constant `0.5`; parameter is not actually honored.
- Tracking quality may degrade when multiple identical classes overlap (identity ambiguity).
- No explicit non-max suppression tuning exposed in config.
- No built-in metrics logger for per-frame latency or dropped-frame rate.

## What to Say in the Review Demo
- "Each frame is inferenced by YOLO, then passed through a temporal tracker to classify movement, not just object class."
- "The output is a structured tuple (name, confidence, direction, position), which is then reused by AI narration."
- "If inference fails on a frame, the system degrades gracefully and continues processing next frames."

## Suggested Engineering Upgrades
- Use the `conf_threshold` argument dynamically in inference call.
- Add per-frame profiling (`inference_ms`, `tracker_ms`, `emit_ms`).
- Make model choice and threshold configurable through environment variables.
- Add synthetic replay tests with fixed video clips for deterministic comparisons.
