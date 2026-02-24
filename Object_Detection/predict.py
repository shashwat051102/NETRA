from ultralytics import YOLO

import cv2

import torch

import time

import os

from pathlib import Path

from Object_Detection.direction_tracker import DirectionTracker

model_path = Path(__file__).parent / "yolov8m.pt"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Using device: {device}")

model = YOLO(str(model_path))

model.to(device)

direction_tracker = DirectionTracker(history_size=10, min_movement_threshold=15)

def detect_objects(frame, conf_threshold=0.5):

    try:

        results = model(frame, conf=0.5, verbose=False)

        detected = []

        detection_w_bbox = []

        frame_height, frame_width = frame.shape[:2]

        for result in results:

            boxes = result.boxes

            for box in boxes:

                x1,y1,x2,y2 = box.xyxy[0].cpu().numpy()

                conf = float(box.conf[0])

                cls = int(box.cls[0])

                name = model.names[cls]

                detection_w_bbox.append((name, conf, (x1,y1,x2,y2)))

        tracked_objects = direction_tracker.update(detection_w_bbox)

        annotated_frame = frame.copy()

        for name,conf,bbox,direction,distance_change in tracked_objects:

            x1,y1,x2,y2 = bbox

            position = direction_tracker.get_position_description(

                bbox,frame_width,frame_height

            )

            color = (0,255,0)

            if "coming towards you" in direction:

                color = (0,0,255)

            elif "moving away" in direction:

                color = (255,0,0)

            cv2.rectangle(annotated_frame, (int(x1),int(y1)), (int(x2),int(y2)), color, 2)

            label = f"{name} {conf:.2f}"

            if direction != "stationary":

                label += f", {direction}"

            label_lines = label.split("|")

            y_offset = int(y1) - 10

            for line in label_lines:

                (label_w,label_h),_= cv2.getTextSize(

                    line.strip(), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1

                )

                cv2.rectangle(annotated_frame,

                            (int(x1), y_offset - label_h - 5),

                            (int(x1) + label_w + 5, y_offset),

                            color, -1)

                cv2.putText(annotated_frame, line.strip(),

                        (int(x1) + 2, y_offset - 3),

                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,

                        (255, 255, 255), 1)

                y_offset -= (label_h + 8)

            detected.append((name,conf,direction,position))

        return detected, annotated_frame

    except Exception as e:

        print(f" Error in detect_objects: {e}")

        import traceback

        traceback.print_exc()

        return [], frame
