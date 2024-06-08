import pyaudio
import wave
import os
import threading
import time
import tkinter as tk
import numpy as np
import speech_recognition as sr

class AudioRecorder:
    def __init__(self):
        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 1
        self.fs = 16000  # Record at 44100 samples per second
        self.seconds_per_save = 3  # Recordings are saved after this duration of silence
        self.frames = []
        self.recording = False
        self.save_count = 0
        self.save_path = r"/Users/vaishnavipraveen/python/recordings"
        self.transcript = ""

        # Creating a folder to store recordings if it doesn't exist
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.paused = False
        self.silence_detected_time = None

        #Initializing the recognizer
        self.recognizer = sr.Recognizer()
        self.transcription_thread = None
        self.transcription_stop_event = threading.Event()

    def start_recording(self):
        if not self.recording:
            threading.Thread(target=lambda: os.system("afplay /System/Library/Sounds/Funk.aiff")).start()
            self.recording = True
            self.transcription_stop_event.clear()  # Clear stop event
            if self.paused:
                self.stream.start_stream()
                self.paused = False
                self.silence_detected_time = time.time()
            else:
                self.frames = []
                self.stream = self.audio.open(format=self.sample_format,
                                              channels=self.channels,
                                              rate=self.fs,
                                              frames_per_buffer=self.chunk,
                                              input=True)
                self.silence_detected_time = time.time()
            #Start transcription thread
            self.transcription_thread = threading.Thread(target=self.transcribe_continuous)
            self.transcription_thread.start()

    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.transcription_stop_event.set()  # Set stop event for transcription thread
            self.stream.stop_stream()
            self.stream.close()
            if self.frames:
                self.save_recording()

    def pause_recording(self):
        if self.recording and not self.paused:
            self.paused = True
            self.stream.stop_stream()

    def resume_recording(self):
        if self.recording and self.paused:
            self.paused = False
            self.stream.start_stream()
            self.silence_detected_time = time.time()  # Reset silence detection time

    def reset_recording(self):
        if self.recording:
            self.frames = []

    def record(self):
        silence_threshold = 100  
        silence_duration_threshold = 3  

        while self.recording:
            data = self.stream.read(self.chunk)
            self.frames.append(data)

            # Convert byte data to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)

            # Calculate RMS (root mean square) to determine if it's silent
            rms = np.sqrt(np.mean(np.square(audio_data)))

            # Check if RMS is below the threshold to detect silence
            if rms < silence_threshold:
                if self.silence_detected_time is None:
                    self.silence_detected_time = time.time()  # Record the time when silence is detected
            else:
                self.silence_detected_time = None  # Reset the silence detection time

            # Check if silence has been detected for more than the threshold duration
            if self.silence_detected_time is not None:
                elapsed_time = time.time() - self.silence_detected_time
                if elapsed_time >= silence_duration_threshold:
                    print("Saving recording...")
                    self.save_recording()
                    self.frames = []  # Reset frames after saving
                    self.silence_detected_time = None  # Reset silence detection time

            if not self.recording:
                print("Recording stopped.")
                self.save_recording()
                break

    def save_recording(self):
        filename = f"{self.save_path}/wave{self.save_count + 1}.wav"
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        self.save_count += 1

    def transcribe_continuous(self):
       while not self.transcription_stop_event.is_set():
            if self.frames:
                audio_data = b''.join(self.frames)
                sample_width = self.audio.get_sample_size(self.sample_format)
                audio_data_obj = sr.AudioData(audio_data, self.fs, sample_width)  
                try:
                    text = self.recognizer.recognize_google(audio_data_obj, language='en-in')
                    print("\rTranscription:", text)
                except sr.UnknownValueError:
                    print("Could not understand audio")
                except sr.RequestError as e:
                    print(f"Error: {e}")

class App:
    def __init__(self, master):
        self.master = master
        self.audio_recorder = AudioRecorder()

        # Create record button
        self.record_button = tk.Button(master, text="Record", command=self.toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Create pause/resume button
        self.pause_button = tk.Button(master, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Create reset button
        self.reset_button = tk.Button(master, text="Reset", command=self.reset_recording)
        self.reset_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.recording = False
        self.paused = False

    def toggle_recording(self):
        if not self.audio_recorder.recording:
            if self.paused:
                self.paused = False
                self.pause_button.config(text="Pause")
            self.audio_recorder.start_recording()
            self.record_button.config(text="Stop Recording")
            # Start recording thread
            recording_thread = threading.Thread(target=self.audio_recorder.record)
            recording_thread.start()
        else:
            self.audio_recorder.stop_recording()
            self.record_button.config(text="Record")

    def toggle_pause(self):
        if not self.paused:
            if self.audio_recorder.recording:
                self.audio_recorder.pause_recording()
            self.paused = True
            self.pause_button.config(text="Resume")
        else:
            if self.audio_recorder.recording:
                self.audio_recorder.resume_recording()
            self.paused = False
            self.pause_button.config(text="Pause")

    def reset_recording(self):
        if self.audio_recorder.frames or self.audio_recorder.recording:
            self.audio_recorder.reset_recording()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
