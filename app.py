import tkinter as tk

from tkinter import ttk, scrolledtext

from PIL import Image, ImageTk

import cv2

import threading

import time

import os

from Object_Detection.predict import detect_objects

from agents.agents import NavigationAgent

from task.task import NavigationTask

from crewai import Crew

from utils.Text_to_speech import text_to_speech

import pygame

class SimpleNavigationApp:

    def __init__(self, root):

        self.root = root

        self.root.title("AI Navigation Assistant")

        self.root.geometry("1000x650")

        pygame.mixer.init()

        agent_factory = NavigationAgent()

        task_factory = NavigationTask()

        self.crew = Crew(

            agents=[agent_factory.navigation_agent()],

            tasks=[task_factory.navigation_task()],

        )

        self.cap = None

        self.running = False

        self.last_instruction_time = 0

        self.instruction_interval = 5.0

        self.setup_ui()

    def setup_ui(self):

        control_frame = ttk.Frame(self.root)

        control_frame.pack(pady=10)

        self.start_btn = ttk.Button(control_frame, text="▶ Start", command=self.start)

        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(control_frame, text="⏸ Stop", command=self.stop, state=tk.DISABLED)

        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.video_label = tk.Label(self.root, bg="black")

        self.video_label.pack(pady=10)

        obj_frame = ttk.LabelFrame(self.root, text="Detected Objects")

        obj_frame.pack(fill=tk.X, padx=20, pady=5)

        self.objects_label = tk.Label(obj_frame, text="", font=("Arial", 10), anchor=tk.W, justify=tk.LEFT)

        self.objects_label.pack(fill=tk.X, padx=10, pady=5)

        inst_frame = ttk.LabelFrame(self.root, text="Navigation Instructions")

        inst_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        self.instructions_text = scrolledtext.ScrolledText(inst_frame, height=8, wrap=tk.WORD, font=("Arial", 10))

        self.instructions_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def start(self):

        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():

            return

        self.running = True

        self.start_btn.config(state=tk.DISABLED)

        self.stop_btn.config(state=tk.NORMAL)

        threading.Thread(target=self.video_loop, daemon=True).start()

    def stop(self):

        self.running = False

        if self.cap:

            self.cap.release()

        pygame.mixer.music.stop()

        self.start_btn.config(state=tk.NORMAL)

        self.stop_btn.config(state=tk.DISABLED)

    def video_loop(self):

        while self.running and self.cap:

            ret, frame = self.cap.read()

            if not ret:

                continue

            detected, annotated_frame = detect_objects(frame)

            rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

            img = Image.fromarray(rgb)

            img = img.resize((640, 480), Image.Resampling.LANCZOS)

            imgtk = ImageTk.PhotoImage(image=img)

            self.video_label.imgtk = imgtk

            self.video_label.config(image=imgtk)

            if detected:

                obj_text = ", ".join([f"{name} ({conf:.2f})" for name, conf in detected])

                self.objects_label.config(text=obj_text)

                current_time = time.time()

                if current_time - self.last_instruction_time >= self.instruction_interval:

                    self.last_instruction_time = current_time

                    threading.Thread(target=self.get_instructions, args=(detected,), daemon=True).start()

            else:

                self.objects_label.config(text="No objects detected")

            time.sleep(0.03)

    def get_instructions(self, detected):

        try:

            object_names = [name for name, conf in detected]

            inputs = {"detect_objects": object_names}

            result = self.crew.kickoff(inputs=inputs)

            instruction_text = str(result)

            timestamp = time.strftime("%H:%M:%S")

            self.instructions_text.insert(tk.END, f"\n[{timestamp}]\n{instruction_text}\n{'-'*50}\n")

            self.instructions_text.see(tk.END)

            audio_file = text_to_speech(instruction_text)

            if audio_file:

                threading.Thread(target=self.play_audio, args=(audio_file,), daemon=True).start()

            print(f"\n[NAVIGATION INSTRUCTION - {timestamp}]:\n{instruction_text}\n")

        except Exception as e:

            print(f"Error: {e}")

    def play_audio(self, audio_file):

        """Play audio using pygame mixer within the app"""

        try:

            if os.path.exists(audio_file):

                print(f"Playing audio: {audio_file}")

                pygame.mixer.music.load(audio_file)

                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():

                    time.sleep(0.1)

                pygame.mixer.music.unload()

                print(f"Finished playing audio: {audio_file}")

            else:

                print(f"Audio file not found: {audio_file}")

        except Exception as e:

            print(f"Error playing audio: {e}")

    def on_closing(self):

        self.running = False

        if self.cap:

            self.cap.release()

        pygame.mixer.quit()

        self.root.destroy()

if __name__ == "__main__":

    root = tk.Tk()

    app = SimpleNavigationApp(root)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    root.mainloop()
