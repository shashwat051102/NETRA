import numpy as np

from collections import deque

import time

class DirectionTracker:

    def __init__(self,history_size = 10, min_movement_threshold = 20):

        """
        Track object movement and direction

        Args:
            history_size: Number of frames to track for each object
            min_movement_threshold: Minimum pixel movement to consider as motion
        """

        self.tracks = {}

        self.history_size = history_size

        self.min_movement_threshold = min_movement_threshold

    def update(self, detections):

        results = []

        current_time = time.time()

        for name,conf, bbox in detections:

            x1,y1,x2,y2 = bbox

            center_x = (x1+x2)/2

            center_y = (y1+y2)/2

            width = x2-x1

            height = y2-y1

            area = width*height

            obj_key = f"{name}_{int(center_x)//100}_{int(center_y)//100}"

            if obj_key not in self.tracks:

                self.tracks[obj_key] = {

                    'positions': deque(maxlen=self.history_size),

                    'areas': deque(maxlen=self.history_size),

                    'times': deque(maxlen=self.history_size)

                }

            track = self.tracks[obj_key]

            track['positions'].append((center_x,center_y))

            track['areas'].append(area)

            track['times'].append(current_time)

            direction = "stationary"

            distance_change = "same distance"

            if len(track['positions']) >=3:

                old_pos = track['positions'][0]

                new_pos = track['positions'][-1]

                old_area = track['areas'][0]

                new_area = track['areas'][-1]

                dx = new_pos[0]-old_pos[0]

                dy = new_pos[1]-old_pos[1]

                area_change_percent = ((new_area-old_area)/old_area)*100

                if abs(dx) > self.min_movement_threshold:

                    if dx > 0:

                        direction = "moving right"

                    else:

                        direction = "moving left"

                if abs(dy) > self.min_movement_threshold:

                    if dy>0:

                        vert_dir = "moving down"

                    else:

                        vert_dir = "moving up"

                    if direction == "stationary":

                        direction = vert_dir

                    else:

                        direction = f"{direction} and {vert_dir}"

                if area_change_percent > 10:

                    distance_change = "coming towards you"

                elif area_change_percent < -10:

                    distance_change = "moving away"

                if distance_change != "same distance":

                    if direction != "stationary":

                        direction = f"{direction}, {distance_change}"

                    else:

                        direction = distance_change

            results.append((name,conf,bbox,direction,distance_change))

        self.cleanup_old_tracks(current_time)

        return results

    def cleanup_old_tracks(self,current_time, max_age=2.0):

        to_remove = []

        for key, track in self.tracks.items():

            if track['times'] and current_time - track['times'][-1] > max_age:

                to_remove.append(key)

        for key in to_remove:

            del self.tracks[key]

    def get_position_description(self,bbox,frame_width, frame_height):

        x1,y1,x2,y2 = bbox

        center_x = (x1+x2)/2

        center_y = (y1+y2)/2

        if center_x < frame_width*0.33:

            h_pos = "left"

        elif center_x > frame_width*0.66:

            h_pos = "right"

        else:

            h_pos = "in front of you"

        if center_y < frame_height*0.33:

            v_pos = "above"

        elif center_y > frame_height*0.66:

            v_pos = "below"

        else:

            v_pos = "at your level"

        if v_pos:

            return f"{h_pos} and {v_pos}"

        return h_pos
