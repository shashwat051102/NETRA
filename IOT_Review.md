# IoT Review (Detailed Code Walkthrough)

## Objective in This Project
The IoT layer adds near-field obstacle awareness using an ultrasonic sensor connected to Arduino, then pushes live distance readings to the web UI for safety alerts.

## Where IoT Logic Lives
- `aurdino.py`: Serial communication adapter class `ArduinoUltrasonic`.
- `flask_app.py`: Background distance thread, emit events, reconnect logic, and start/stop lifecycle hooks.
- `templates/index.html`: Distance panel rendering and beep trigger handling.

## Hardware and Communication
- Sensor setup assumes HC-SR04-like distance output sent by Arduino over serial.
- Python side uses `pyserial` with defaults: baudrate `9600`, timeout `1` second.
- Default runtime port in app flow: `ARDUINO_PORT` environment variable or `COM11` fallback.

## Serial Adapter Behavior (`aurdino.py`)
1. `connect()`:
- Opens serial port (`serial.Serial(port, baudrate, timeout)`).
- Waits 2 seconds to allow Arduino reset.
- Clears initial serial buffer.
- Marks `connected=True` and returns success.

2. `read_distance()`:
- Clears input buffer for fresh data.
- Sleeps briefly (`0.15s`) to accumulate latest line.
- Reads lines from serial buffer and attempts float parsing.
- Ignores non-distance setup messages (for example, "Ultrasonic Sensor Ready").
- Returns parsed distance as float or `None`.

3. Connection status methods:
- `is_connected()` verifies open serial state.
- `close()` safely releases port.

## Detailed Read Cycle (`read_distance`) What Happens Per Call
1. Validates serial object is open; otherwise returns `None`.
2. Calls `reset_input_buffer()` to avoid stale values.
3. Sleeps for `0.15s` to allow fresh UART bytes to arrive.
4. Loops up to 5 attempts while `in_waiting > 0`.
5. For each line:
- Decodes UTF-8 and strips whitespace.
- Ignores non-numeric boot/status lines.
- Tries `float(line)` conversion.
6. Returns first valid float found, else `None`.

## IoT State Variables in `flask_app.py`
- `arduino_sensor`: Active `ArduinoUltrasonic` object.
- `arduino_thread`: Background worker reading serial continuously.
- `arduino_running`: Boolean control flag for worker loop.
- `last_distance`: Last valid numeric reading cached for app state.

## Flask IoT Thread Flow (`flask_app.py`)
1. Trigger point:
- In `handle_start()`, Arduino thread starts when detection starts or if previous thread died.

2. `arduino_distance_loop()`:
- Initializes `ArduinoUltrasonic` with selected port.
- If connect fails:
- Emits `arduino_status` disconnected message.
- Disables loop by setting `arduino_running=False`.

3. Main loop (every ~0.5s):
- Calls `read_distance()`.
- If valid positive value:
- Updates `last_distance`.
- Computes `should_beep = distance < 50`.
- Emits `distance_data` event with `distance`, timestamp, and beep boolean.
- If not connected:
- Attempts serial reconnect and emits status updates.

## Distance Threshold Logic in Code
- Threshold check is explicit: `should_beep = distance < 50`.
- Backend does not play sound directly; it sends boolean `beep` in socket payload.
- Frontend decides when/how to play beep, including throttle protection (`>=400ms` gap).

## Frontend Sound and UI Reaction Path
1. Receives `distance_data`.
2. Updates `distanceDisplay` text to `xx.x cm`.
3. Updates `distanceStatus` with timestamp.
4. Applies safety color rule:
- Red if `<10`.
- Orange if `<30`.
- Blue otherwise.
5. If `beep` is true, executes `playBeep()`.
6. `playBeep()` creates oscillator tone in Web Audio API and rate-limits repeated beeps.

## Failure and Recovery Behavior
- If initial serial connect fails, backend emits disconnected status and stops IoT loop.
- If disconnection happens during run, loop attempts reconnect and emits reconnect status.
- On stop/exit, adapter `close()` releases COM port to avoid lock persistence.

4. Stop behavior:
- `stop_detection` sets flags to stop real-time operations.
- On loop exit, Arduino connection is closed.

## Frontend IoT Behavior (`index.html`)
- Listens to `distance_data`:
- Displays formatted distance in centimeters.
- Updates "Last update" timestamp text.
- Applies color coding:
- `< 10 cm`: red (very close)
- `< 30 cm`: orange (close)
- Otherwise: blue (safe)
- If `beep=true`, calls `playBeep()` with throttle protection.

- Listens to `arduino_status`:
- Shows connection status text (connected/disconnected/reconnecting).
- Colors status indicator accordingly.

## Strengths in Current IoT Implementation
- Real-time sensor loop is integrated into same Socket.IO channel as vision and AI.
- Auto-reconnect logic reduces manual restarts.
- Simple threshold-to-beep feedback improves immediate user awareness.
- Sensor adapter is isolated from web logic for cleaner maintenance.

## Technical Risks / Review Notes
- COM port defaults are machine-specific and can break on deployment changes.
- Serial port conflicts may occur if another tool is currently monitoring same COM port.
- Raw readings are not smoothed, so jitter can cause inconsistent beep behavior.
- No explicit calibration UI/workflow for different mounting heights and angles.

## What to Say in the Review Demo
- "When Start is clicked, the backend launches a dedicated Arduino distance thread."
- "Every half-second, distance is read and pushed to UI as live telemetry."
- "A beep flag is derived from threshold logic so the browser can alert the user immediately."

## Suggested Engineering Upgrades
- Add selectable serial port dropdown in UI with runtime reconnect action.
- Add moving-average/median filtering and hysteresis around beep threshold.
- Log sensor uptime metrics: reconnect count, invalid read rate, last update age.
- Add support for additional sensors through a shared hardware interface abstraction.
