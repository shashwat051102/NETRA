#  Direction Tracking Algorithm - Complete Guide

##  Overview

This document explains how the Direction Tracker works to detect object movement in real-time video using YOLOv8 and computer vision principles.

---

##  Core Concept: Tracking Movement Over Time

The algorithm compares object positions across multiple frames to determine:
1. **Horizontal movement** (left/right)
2. **Vertical movement** (up/down)  
3. **Depth movement** (coming closer/going away)

---

##  Algorithm Breakdown

### Step 1: Initialize the Tracker

```python
class DirectionTracker:
    def __init__(self, history_size=10, min_movement_threshold=20):
        self.tracks = {}  # Store tracking history for each object
        self.history_size = history_size  # Number of frames to remember
        self.min_movement_threshold = min_movement_threshold  # Minimum pixels to count as movement
```

**Parameters:**
- `history_size = 10`: Remember last 10 frames
- `min_movement_threshold = 20`: Ignore movements smaller than 20 pixels (reduces noise)

---

### Step 2: Calculate Object Properties

```python
# Get bounding box coordinates from YOLO
x1, y1, x2, y2 = bbox  # Top-left and bottom-right corners

# Calculate center point
center_x = (x1 + x2) / 2
center_y = (y1 + y2) / 2

# Calculate size
width = x2 - x1
height = y2 - y1
area = width * height
```

**What we extract:**
- **Center point (x, y)**: WHERE the object is in the frame
- **Area**: HOW BIG the object appears (indicates distance)

**Visual Example:**
```
Bounding Box:
(x1, y1) = (100, 200)  ┌─────────┐
                       │         │
(x2, y2) = (200, 400)  └─────────┘

Center: ((100+200)/2, (200+400)/2) = (150, 300)
Width: 200 - 100 = 100 pixels
Height: 400 - 200 = 200 pixels
Area: 100 × 200 = 20,000 pixels²
```

---

### Step 3: Create Unique Object ID

```python
obj_key = f"{name}_{int(center_x)//100}_{int(center_y)//100}"
```

**Purpose:** Track the SAME object across multiple frames

**How it works:**
- Divides frame into 100×100 pixel grid cells
- Objects in the same region get the same ID
- Prevents creating new tracks for same object

**Example:**
```
Frame 1: Person at (520, 340) → ID: "person_5_3"
Frame 2: Person at (530, 345) → ID: "person_5_3" (same!)
Frame 3: Person at (540, 350) → ID: "person_5_3" (tracking continues)
```

**Why group by region?**
- Objects move slightly between frames
- Grouping keeps tracking consistent
- Prevents duplicate tracks for same object

---

### Step 4: Store Position History

```python
if obj_key not in self.tracks:
    self.tracks[obj_key] = {
        'positions': deque(maxlen=self.history_size),
        'areas': deque(maxlen=self.history_size),
        'times': deque(maxlen=self.history_size)
    }

track = self.tracks[obj_key]
track['positions'].append((center_x, center_y))
track['areas'].append(area)
track['times'].append(current_time)
```

**Data Structure:**
- `deque`: A list that automatically removes oldest items when full
- Stores last 10 frames of data (configurable)

**What we store:**
- **positions**: List of (x, y) coordinates
- **areas**: List of bounding box sizes
- **times**: Timestamps for each detection

**Example History:**
```
Frame 1: position=(100, 200), area=5000,  time=1.00
Frame 2: position=(105, 200), area=5100,  time=1.03
Frame 3: position=(110, 200), area=5200,  time=1.06
Frame 4: position=(115, 200), area=5300,  time=1.09
...
Frame 10: position=(145, 200), area=5900, time=1.27
```

---

### Step 5: Calculate Movement Deltas

```python
if len(track['positions']) >= 3:
    # Compare first and last positions
    old_pos = track['positions'][0]   # Oldest position
    new_pos = track['positions'][-1]  # Newest position
    old_area = track['areas'][0]
    new_area = track['areas'][-1]
    
    # Calculate changes
    dx = new_pos[0] - old_pos[0]  # Horizontal change
    dy = new_pos[1] - old_pos[1]  # Vertical change
```

**Delta Calculation:**
- `dx`: Change in X coordinate (horizontal movement)
- `dy`: Change in Y coordinate (vertical movement)

**Example:**
```
Old position: (100, 200)
New position: (150, 180)

dx = 150 - 100 = +50 pixels → Moved RIGHT
dy = 180 - 200 = -20 pixels → Moved UP
```

**Sign Convention:**
- `dx > 0`: Object moved RIGHT
- `dx < 0`: Object moved LEFT
- `dy > 0`: Object moved DOWN (Y increases downward in images)
- `dy < 0`: Object moved UP

---

### Step 6: Detect Horizontal Movement

```python
if abs(dx) > self.min_movement_threshold:
    if dx > 0:
        direction = "moving right"
    else:
        direction = "moving left"
```

**Logic:**
1. Check if movement is significant (`abs(dx) > 20`)
2. Determine direction based on sign

**Why use `abs()` and threshold?**
- Filter out camera shake
- Ignore tiny jitter
- Only report meaningful movement

**Real-World Examples:**
```
Person: dx = +45 pixels
abs(45) = 45 > 20 
dx > 0 → "moving right"

Car: dx = -35 pixels
abs(-35) = 35 > 20 
dx < 0 → "moving left"

Stationary object: dx = +8 pixels
abs(8) = 8 < 20 
Ignored (camera shake)
```

---

### Step 7: Detect Vertical Movement

```python
if abs(dy) > self.min_movement_threshold:
    if dy > 0:
        vert_dir = "moving down"
    else:
        vert_dir = "moving up"
    
    # Combine with horizontal direction
    if direction == "stationary":
        direction = vert_dir
    else:
        direction = f"{direction} and {vert_dir}"
```

**Same logic as horizontal, but for Y-axis**

**Image Coordinate System:**
```
(0,0) ──────────→ X (right)
 │
 │
 │
 ↓ Y (down)
```

**Examples:**
```
Diagonal movement:
dx = +30, dy = +25
→ "moving right and moving down"

Pure vertical:
dx = 5, dy = -30
→ "moving up"
```

---

### Step 8: Detect Depth Movement ( KEY INNOVATION)

```python
# Calculate area change percentage
area_change_percent = ((new_area - old_area) / old_area) * 100

if area_change_percent > 10:
    distance_change = "coming towards you"
elif area_change_percent < -10:
    distance_change = "moving away"
else:
    distance_change = "same distance"
```

**The Physics Behind It:**

**Perspective Projection Principle:**
- Objects appear **LARGER** when they get **CLOSER**
- Objects appear **SMALLER** when they move **FARTHER**

**Mathematical Example:**

```
Scenario: Person walking towards camera

Frame 1: 
Bounding box: 100×200 pixels
Area: 20,000 px²

Frame 10:
Bounding box: 120×240 pixels
Area: 28,800 px²

Calculation:
area_change = (28,800 - 20,000) / 20,000 × 100
            = 8,800 / 20,000 × 100
            = 44% increase

44% > 10% → "coming towards you" 
```

**Why 10% threshold?**
- Small changes: Camera angle, lighting, detection variance
- 10%: Significant enough to indicate real movement
- Adjustable based on camera setup

**Real-World Examples:**

| Scenario | Old Area | New Area | Change | Result |
|----------|----------|----------|--------|--------|
| Person approaching | 10,000 | 13,000 | +30% | "coming towards you" |
| Car driving away | 50,000 | 40,000 | -20% | "moving away" |
| Stationary object | 15,000 | 15,500 | +3% | "same distance" |

---

### Step 9: Combine All Directions

```python
if distance_change != "same distance":
    if direction != "stationary":
        direction = f"{direction}, {distance_change}"
    else:
        direction = distance_change
```

**Creates Natural Language Output:**

| Horizontal | Vertical | Depth | Final Output |
|------------|----------|-------|--------------|
| +30 | 0 | +15% | "moving right, coming towards you" |
| -25 | 0 | -12% | "moving left, moving away" |
| 5 | 3 | +20% | "coming towards you" |
| +30 | -25 | +5% | "moving right and moving up" |
| 0 | +35 | -8% | "moving down" |

**Priority Logic:**
1. Show horizontal/vertical movement first
2. Add depth information if significant
3. If only depth movement, show that alone

---

### Step 10: Relative Position Detection

```python
def get_position_description(self, bbox, frame_width, frame_height):
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    
    # Horizontal position (divide into thirds)
    if center_x < frame_width * 0.33:
        h_pos = "on your left"
    elif center_x > frame_width * 0.67:
        h_pos = "on your right"
    else:
        h_pos = "in front of you"
    
    # Vertical position
    if center_y < frame_height * 0.33:
        v_pos = "above"
    elif center_y > frame_height * 0.67:
        v_pos = "below"
    else:
        v_pos = ""
    
    # Combine
    if v_pos:
        return f"{h_pos} and {v_pos}"
    return h_pos
```

**Frame Division:**

```
Horizontal (640px wide):
|----LEFT----|---CENTER---|---RIGHT----|
0          213          427          640
   33%            67%

Vertical (480px high):
|---ABOVE---|
|--CENTER---|
|---BELOW---|
```

**Examples:**
```
Object at (100, 240) in 640×480 frame:
center_x = 100 < 213 → LEFT
center_y = 240 (middle) → CENTER
Result: "on your left"

Object at (500, 100):
center_x = 500 > 427 → RIGHT
center_y = 100 < 160 → ABOVE
Result: "on your right and above"
```

---

### Step 11: Cleanup Old Tracks

```python
def _cleanup_old_tracks(self, current_time, max_age=2.0):
    to_remove = []
    for key, track in self.tracks.items():
        if track['times'] and current_time - track['times'][-1] > max_age:
            to_remove.append(key)
    
    for key in to_remove:
        del self.tracks[key]
```

**Purpose:** Remove objects not seen recently

**Why needed?**
- Objects leave the frame
- Objects get occluded (hidden behind something)
- Prevents memory bloat
- Stops tracking "ghost" objects

**Example:**
```
Time: 10.00s - Person detected
Time: 10.50s - Person still visible
Time: 11.00s - Person leaves frame
Time: 13.01s - Cleanup runs (11.00 + 2.0 > 13.01)
          → Remove person track
```

---

##  Complete Workflow Example

**Scenario:** Person walking towards camera from left side

### Frame 1 (Time: 0.00s)
```
Detection: person
Position: (100, 300)
Area: 10,000 px²
Actions:
- Create new track "person_1_3"
- Store: positions=[(100,300)], areas=[10000]
- Not enough history yet
Output: "stationary"
```

### Frame 5 (Time: 0.15s)
```
Detection: person
Position: (180, 310)
Area: 14,000 px²
Calculations:
- dx = 180 - 100 = 80 pixels
- dy = 310 - 300 = 10 pixels
- area_change = (14000-10000)/10000*100 = 40%
Evaluation:
- abs(80) > 20 , dx > 0 → "moving right"
- abs(10) < 20  → ignore vertical
- 40% > 10%  → "coming towards you"
Output: "moving right, coming towards you"
```

### Frame 10 (Time: 0.30s)
```
Detection: person
Position: (260, 320)
Area: 19,600 px²
Calculations:
- dx = 260 - 100 = 160 pixels
- dy = 320 - 300 = 20 pixels
- area_change = (19600-10000)/10000*100 = 96%
Evaluation:
- abs(160) > 20  → "moving right"
- abs(20) = 20 (borderline)
- 96% > 10%  → "coming towards you"
Output: "moving right, coming towards you"
Position: center_x=260, frame_width=640
         260 < 640*0.33=213? No
         260 > 640*0.67=427? No
         → "in front of you"
Final: "Person in front of you, moving right, coming towards you"
```

---

##  Key Computer Vision Principles

### 1. **Temporal Tracking**
- **Concept**: Use time-series data to detect patterns
- **Application**: Compare positions across frames
- **Benefit**: Single frame = position, Multiple frames = motion

### 2. **Perspective Projection**
- **Concept**: 3D world → 2D image transformation
- **Formula**: `apparent_size ∝ 1/distance`
- **Application**: Bigger bounding box = closer object

### 3. **Optical Flow**
- **Concept**: Pattern of apparent motion between frames
- **Application**: Track center point movement
- **Benefit**: Detect direction without 3D coordinates

### 4. **Noise Filtering**
- **Concept**: Ignore small variations
- **Application**: 20-pixel threshold
- **Benefit**: Robust to camera shake, detection jitter

### 5. **Spatial Quantization**
- **Concept**: Divide continuous space into discrete regions
- **Application**: 100×100 pixel grid for object IDs
- **Benefit**: Consistent tracking despite minor position shifts

---

##  Mathematical Formulas Summary

### Movement Calculation
```
dx = x_new - x_old
dy = y_new - y_old
distance_moved = √(dx² + dy²)
```

### Area Change Percentage
```
area_change_percent = ((area_new - area_old) / area_old) × 100

if area_change_percent > 10%:
    → Object getting closer (approaching)
if area_change_percent < -10%:
    → Object getting farther (receding)
```

### Position Classification
```
Horizontal:
- LEFT:   center_x < frame_width × 0.33
- CENTER: 0.33 ≤ center_x/frame_width ≤ 0.67
- RIGHT:  center_x > frame_width × 0.67

Vertical:
- ABOVE:  center_y < frame_height × 0.33
- MIDDLE: 0.33 ≤ center_y/frame_height ≤ 0.67
- BELOW:  center_y > frame_height × 0.67
```

---

##  Why This Approach Works

### Advantages:
 **No 3D sensors needed** - Works with regular webcam  
 **Computationally efficient** - Simple arithmetic  
 **Real-time capable** - Runs at 30 FPS  
 **Robust to noise** - Threshold filtering  
 **Natural language output** - Easy for blind users to understand  

### Limitations:
 **No exact distance** - Only relative (closer/farther)  
 **Assumes single object** - Multiple same-type objects can confuse ID  
 **Sensitive to camera movement** - Needs stable camera  
 **2D approximation** - Not true 3D tracking  

### Trade-offs:
- **Accuracy vs Speed**: 10 frame history balances both
- **Sensitivity vs Noise**: 20-pixel threshold is compromise
- **Memory vs History**: 10 frames keeps memory low

---

##  Performance Optimization Tips

### 1. Adjust History Size
```python
# More history = smoother but slower
DirectionTracker(history_size=15)  

# Less history = faster but jittery
DirectionTracker(history_size=5)
```

### 2. Tune Movement Threshold
```python
# Stricter (less sensitive)
DirectionTracker(min_movement_threshold=30)

# More sensitive
DirectionTracker(min_movement_threshold=10)
```

### 3. Area Change Threshold
```python
# In update() method, change:
if area_change_percent > 15:  # Stricter for "approaching"
if area_change_percent < -15:  # Stricter for "receding"
```

---

##  Learning Resources

### Computer Vision Concepts:
- **Optical Flow**: Lucas-Kanade method
- **Object Tracking**: Kalman Filter, SORT algorithm
- **Perspective Geometry**: Camera calibration

### Related Algorithms:
- **DeepSORT**: Advanced multi-object tracking
- **Centroid Tracking**: Simpler alternative
- **IoU Tracking**: Intersection over Union based

### Python Libraries:
- `collections.deque`: Efficient queue data structure
- `numpy`: Fast numerical operations
- `opencv`: Computer vision functions

---

##  Summary

This direction tracking algorithm:
1. **Tracks** object positions over time using a sliding window
2. **Calculates** movement by comparing old and new positions
3. **Detects** horizontal, vertical, and depth movement
4. **Filters** noise using thresholds
5. **Generates** natural language descriptions for blind users

**Core Innovation:** Using bounding box area changes to estimate depth movement without 3D sensors!

---

##  Integration with Navigation System

```python
# In flask_app.py
detected, annotated_frame = detect_objects(frame)

# detected now contains:
# [(name, conf, direction, position), ...]
# Example: ("person", 0.95, "moving right, coming towards you", "on your left")

# This enriched data is sent to:
# 1. Browser UI - Visual display
# 2. CrewAI agents - Generate instructions
# 3. TTS system - Audio warnings
```

---

**Made with  for Blind Navigation Assistant Project**