try:
    import eventlet
    eventlet.monkey_patch()
    USE_EVENTLET = True
except Exception:
    USE_EVENTLET = False

from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
import cv2
import threading
import time
import base64
import os
from Object_Detection.predict import detect_objects
from aurdino import ArduinoUltrasonic

# Try to import AI agent features (optional)
try:
    from agents.agents import NavigationAgent
    from task.task import NavigationTask
    from crewai import Crew
    from utils.Text_to_speech import text_to_speech, text_to_speech_b64
    AI_ENABLED = True
    print(" ✓ AI Navigation features loaded")
except ImportError as e:
    AI_ENABLED = False
    print(f" ⚠ AI Navigation disabled due to import error: {e}")
    # Fallback functions
    def text_to_speech_b64(text):
        return None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=('eventlet' if USE_EVENTLET else 'threading'))

# Initialize AI crew if available
if AI_ENABLED:
    agent_factory = NavigationAgent()
    task_factory = NavigationTask()
    crew = Crew(
        agents=[agent_factory.navigation_agent()],
        tasks=[task_factory.navigation_task()],
    )
else:
    crew = None

camera = None
running = False
last_instruction_time = 0
instruction_interval = 15.0
next_instruction_ready_at = 0.0
is_generating_instruction = False
current_audio_thread = None
last_detected_objects = []

# Arduino ultrasonic sensor
arduino_sensor = None
arduino_thread = None
arduino_running = False
last_distance = None


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')

def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    """Generate video frames for streaming"""
    global camera, running, last_instruction_time, is_generating_instruction, next_instruction_ready_at
    if camera is None:
        src = os.environ.get('VIDEO_SOURCE') or '0'
        try:
            src_val = int(src)
        except ValueError:
            src_val = src
        def _open_capture(val):
            if isinstance(val, int):
                return cv2.VideoCapture(val)
            cap = cv2.VideoCapture(val)
            if cap.isOpened():
                return cap
            return cv2.VideoCapture(val, cv2.CAP_FFMPEG)
        print(f" Opening video source: {src!r}")
        camera = _open_capture(src_val)
        if not camera or not camera.isOpened():
            print(" Error: Could not open camera/video source. Set VIDEO_SOURCE to rtsp/http/mp4 or use 0/1 for device.")
            try:
                socketio.emit('status', {'running': False, 'message': 'Could not open video source'})
            except Exception:
                pass

            return

        print(" Camera initialized")

    while True:
        try:
            success, frame = camera.read()
            if not success:
                print(" Failed to read frame")
                time.sleep(0.1)
                continue
            if running:
                try:
                    detected, annotated_frame = detect_objects(frame)
                    try:
                        global last_detected_objects
                        last_detected_objects = detected or []
                    except Exception:
                        pass
                    if detected:
                        obj_list = []
                        for name, conf, direction, position in detected:
                            obj_list.append({
                                "name": name,
                                "confidence": float(conf),
                                "direction": direction,
                                "position": position
                            })
                        socketio.emit('detected_objects', {'objects': obj_list})
                        current_time = time.time()
                        if current_time >= next_instruction_ready_at and not is_generating_instruction:
                            is_generating_instruction = True
                            print(" LOCKED - Starting instruction generation")
                            socketio.start_background_task(get_instructions, detected)
                    else:
                        socketio.emit('detected_objects', {'objects': []})
                        current_time = time.time()
                        if current_time >= next_instruction_ready_at and not is_generating_instruction:
                            is_generating_instruction = True
                            print(" LOCKED - Starting instruction generation (no objects)")
                            socketio.start_background_task(get_instructions, [])
                except Exception as e:
                    print(f" Error in detection: {e}")

                    import traceback

                    traceback.print_exc()

                    annotated_frame = frame

            else:

                annotated_frame = frame

            ret, buffer = cv2.imencode('.jpg', annotated_frame)

            if not ret:

                print(" Failed to encode frame")

                continue

            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'

                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        except Exception as e:

            print(f" Error in generate_frames: {e}")

            import traceback

            traceback.print_exc()

            time.sleep(0.1)

@socketio.on('client_frame')

def handle_client_frame(data):

    """Receive a frame from the client (browser camera), run detection, and emit results."""

    global running, is_generating_instruction, next_instruction_ready_at, last_detected_objects

    try:

        if not running:

            return

        if not data:

            return

        img_b64 = data.get('image') or data.get('frame')

        if not img_b64:

            return

        if isinstance(img_b64, str) and img_b64.startswith('data:image'):

            comma = img_b64.find(',')

            if comma != -1:

                img_b64 = img_b64[comma+1:]

        import numpy as np

        img_bytes = base64.b64decode(img_b64)

        np_arr = np.frombuffer(img_bytes, np.uint8)

        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:

            return

        detected, _ = detect_objects(frame)

        obj_list = []

        if detected:

            for name, conf, direction, position in detected:

                obj_list.append({

                    'name': name,

                    'confidence': float(conf),

                    'direction': direction,

                    'position': position

                })

        socketio.emit('detected_objects', {'objects': obj_list})

        try:

            last_detected_objects = detected or []

        except Exception:

            pass

        current_time = time.time()

        if current_time >= next_instruction_ready_at and not is_generating_instruction:

            is_generating_instruction = True

            socketio.start_background_task(get_instructions, last_detected_objects)

    except Exception as e:

        print(f" Error in handle_client_frame: {e}")

        import traceback

        traceback.print_exc()

def get_instructions(detected):
    """Generate navigation instructions using AI"""
    global is_generating_instruction, current_audio_thread
    try:
        print("[get_instructions] entered; will emit text then audio if available")
        print("\n" + "="*60)
        print(" Starting instruction generation")
        print("="*60)
        object_info = []
        for name, conf, direction, position in detected:
            info = f"{name} {position}"
            if direction != "stationary":
                info += f" ({direction})"
            object_info.append(info)
        print(f" Objects detected: {object_info}")
        inputs = {"detect_objects": object_info}
        print(" Generating AI instruction...")
        def _simple_instruction(objs):
            if not objs:
                return "No obstacles detected ahead."
            if len(objs) == 1:
                return f"There is {objs[0]}. Please proceed with caution."
            return "Detected: " + ", ".join(objs) + ". Please proceed carefully."
        
        result_holder = {"text": None, "error": None}
        
        # Only try AI generation if crew is available
        if AI_ENABLED and crew is not None:
            def _run_kickoff():
                try:
                    res = crew.kickoff(inputs=inputs)
                    result_holder["text"] = str(res)
                except Exception as e:
                    result_holder["error"] = e
            kickoff_thread = threading.Thread(target=_run_kickoff, daemon=True)
            kickoff_thread.start()
            kickoff_thread.join(timeout=6.0)
        
        if result_holder["text"] is not None:
            instruction_text = result_holder["text"]
        else:
            if result_holder["error"] is not None:
                print(f" LLM generation failed, using simple fallback: {result_holder['error']}")
            elif AI_ENABLED:
                print("⏱ LLM generation timed out, using simple fallback")
            else:
                print(" Using simple instruction (AI disabled)")
            instruction_text = _simple_instruction(object_info)
        print(f" Generated instruction: {instruction_text[:100]}...")
        print(" Generating audio (in-memory) to send with text...")
        audio_b64 = None
        if AI_ENABLED:
            try:
                audio_b64 = text_to_speech_b64(instruction_text)
                if audio_b64:
                    print(f" Audio ready, size: {len(audio_b64)} chars")
            except Exception as e:
                print(f" Audio generation failed, sending text only: {e}")
        else:
            print(" Audio generation skipped (AI disabled)")
        payload = {
            'instruction': instruction_text,
            'timestamp': time.strftime("%H:%M:%S")
        }
        if audio_b64:
            payload['audio'] = audio_b64
        socketio.emit('navigation_instruction', payload)
        print(" Instruction and audio sent together")
        global next_instruction_ready_at, last_instruction_time
        last_instruction_time = time.time()
        next_instruction_ready_at = last_instruction_time + instruction_interval
        print(f"⏱ Next instruction at {time.strftime('%H:%M:%S', time.localtime(next_instruction_ready_at))} (+{instruction_interval:.0f}s)")
    except Exception as e:
        print(f" Error in get_instructions: {e}")
        import traceback
        traceback.print_exc()
    finally:
        is_generating_instruction = False

@socketio.on('connect')

def handle_connect():

    print('\n' + '='*60)

    print(' CLIENT CONNECTED')

    print('='*60)

    print(f'   Client ID: {request.sid}')

    print(f'   Time: {time.strftime("%H:%M:%S")}')

    print('='*60 + '\n')

    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')

def handle_disconnect():

    print('\n' + '='*60)

    print(' CLIENT DISCONNECTED')

    print('='*60)

    print(f'   Client ID: {request.sid}')

    print(f'   Time: {time.strftime("%H:%M:%S")}')

    print('='*60 + '\n')

@socketio.on('start_detection')

def handle_start():

    global running, last_instruction_time, is_generating_instruction, last_detected_objects, next_instruction_ready_at
    global arduino_running, arduino_thread

    print('\n' + '='*60)

    print(' RECEIVED START DETECTION EVENT')

    print('='*60)

    print(f'   Client ID: {request.sid}')

    print(f'   Time: {time.strftime("%H:%M:%S")}')

    print(f'   Previous running state: {running}')

    running = True

    print(f'   New running state: {running}')
    
    # Start Arduino distance monitoring.
    # Also recover if a previous Arduino thread exited unexpectedly.
    if (not arduino_running) or (arduino_thread is not None and not arduino_thread.is_alive()):
        arduino_running = True
        arduino_thread = threading.Thread(target=arduino_distance_loop, daemon=True)
        arduino_thread.start()
        print(' Arduino distance monitoring started')

    print('='*60)

    emit('status', {'running': True, 'message': 'Detection started'})

    print(' Status emitted to client')

    print('='*60 + '\n')

    try:

        if not is_generating_instruction:

            is_generating_instruction = True

            print(' Immediate instruction kickoff after start')

            last_instruction_time = time.time()

            next_instruction_ready_at = last_instruction_time

            socketio.start_background_task(get_instructions, last_detected_objects or [])

    except Exception as e:

        print(f" Could not trigger immediate instruction: {e}")

def arduino_distance_loop():
    """Background thread to read Arduino distance every 0.5 seconds"""
    global arduino_sensor, arduino_running, last_distance
    
    # Initialize Arduino
    arduino_port = os.environ.get('ARDUINO_PORT', 'COM11')
    arduino_sensor = ArduinoUltrasonic(port=arduino_port, baudrate=9600)
    
    if not arduino_sensor.connect():
        print(" ⚠ Arduino sensor not connected. Distance monitoring disabled.")
        socketio.emit('arduino_status', {'connected': False, 'message': 'Arduino not connected'})
        arduino_running = False
        return
    
    print(" ✓ Arduino sensor connected. Starting distance monitoring...")
    socketio.emit('arduino_status', {'connected': True, 'message': 'Arduino connected'})
    
    while arduino_running:
        try:
            distance = arduino_sensor.read_distance()
            
            if distance is not None and distance > 0:
                last_distance = distance
                print(f" 📏 Distance: {distance:.2f} cm")
                
                # Check if beep needed (< 50cm)
                should_beep = distance < 50
                
                socketio.emit('distance_data', {
                    'distance': round(distance, 2),
                    'timestamp': time.strftime("%H:%M:%S"),
                    'beep': should_beep
                })
            else:
                # Try to reconnect if disconnected
                if not arduino_sensor.is_connected():
                    print(" ⚠ Arduino disconnected. Attempting to reconnect...")
                    socketio.emit('arduino_status', {'connected': False, 'message': 'Reconnecting...'})
                    if arduino_sensor.connect():
                        print(" ✓ Arduino reconnected")
                        socketio.emit('arduino_status', {'connected': True, 'message': 'Reconnected'})
            
            # Wait 0.5 seconds before next reading (faster updates)
            time.sleep(0.5)
            
        except Exception as e:
            print(f" ✗ Error in Arduino loop: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(0.5)
    
    # Cleanup
    if arduino_sensor:
        arduino_sensor.close()
    print(" ✓ Arduino distance monitoring stopped")

@socketio.on('stop_detection')

def handle_stop():

    global running, arduino_running

    print('\n' + '='*60)

    print(' RECEIVED STOP DETECTION EVENT')

    print('='*60)

    print(f'   Client ID: {request.sid}')

    print(f'   Time: {time.strftime("%H:%M:%S")}')

    print(f'   Previous running state: {running}')

    running = False

    print(f'   New running state: {running}')

    print('='*60)

    emit('status', {'running': False, 'message': 'Detection stopped'})

    print('⏸ Status emitted to client')

    print('='*60 + '\n')

@app.route('/tts_test')

def tts_test():

    """Quick endpoint to test text-to-speech on the server and return base64 length."""

    try:

        sample = "This is a quick TTS test from the server."

        print('\n Running /tts_test with sample text...')

        audio_file = text_to_speech(sample)

        if audio_file and os.path.exists(audio_file):

            with open(audio_file, 'rb') as f:

                data = f.read()

            audio_b64 = base64.b64encode(data).decode('utf-8')

            try:

                os.remove(audio_file)

            except Exception as e:

                print(f" Could not remove tts test file: {e}")

            print(f" /tts_test generated audio, size={len(audio_b64)} chars")

            return jsonify({'ok': True, 'b64_length': len(audio_b64)})

        else:

            print(" /tts_test failed to generate audio file")

            return jsonify({'ok': False, 'error': 'no_audio_file'})

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({'ok': False, 'error': str(e)})

if __name__ == '__main__':

    print(" Starting Flask app...")

    port = int(os.environ.get('PORT', '5000'))

    print(f" Server will be available at: http://localhost:{port}")

    run_kwargs = dict(host='0.0.0.0', port=port, debug=False)

    if not USE_EVENTLET:

        run_kwargs['allow_unsafe_werkzeug'] = True

    socketio.run(app, **run_kwargs)
