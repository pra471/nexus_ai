import os
import webbrowser
import datetime
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import speech_recognition as sr
import pyttsx3
import pvporcupine
import pyaudio
import struct
import tkinter as tk
import json
import threading
from queue import Queue

# --- Configuration ---
# IMPORTANT: Paste your keys here
GOOGLE_API_KEY = "AIzaSyBE4voEab4qTmOTFmdykQnKqZvA0qE6OnY"
PICOVOICE_ACCESS_KEY = "4AX6Pag04YDmlLoaixQz4Q4fpVr5wCsL0d0EBUU/E6btMBFKrMu8og=="

# --- Setup ---
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
porcupine = pvporcupine.create(access_key=PICOVOICE_ACCESS_KEY, keywords=['computer'])
recognizer = sr.Recognizer()
recognizer.energy_threshold = 3000
recognizer.dynamic_energy_threshold = False
pa = pyaudio.PyAudio()

# --- Memory Functions ---
MEMORY_FILE = "memory.json"

def save_to_memory(key, value):
    """Saves a key-value pair to the memory file."""
    try:
        with open(MEMORY_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    
    data[key] = value
    with open(MEMORY_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    speak(f"Okay, I'll remember that {key} is {value}.")

def recall_from_memory(key):
    """Recalls a value from the memory file based on a key."""
    try:
        with open(MEMORY_FILE, 'r') as f:
            data = json.load(f)
            value = data.get(key)
            if value:
                speak(f"You told me that {key} is {value}.")
            else:
                speak(f"I don't have any memory of {key}.")
    except FileNotFoundError:
        speak("I don't have any memories yet.")

# --- GUI Functions ---
def update_gui(message, sender="Nova"):
    """Updates the GUI with a new message in a thread-safe way."""
    gui_queue.put(f"{sender}: {message}\n")

def process_gui_queue(text_widget, status_label):
    """Processes messages from the queue and updates the GUI."""
    should_exit = False
    while not gui_queue.empty():
        message = gui_queue.get_nowait()
        if message == "EXIT_GUI":
            should_exit = True
            continue
        if "STATUS:" in message:
            status_label.config(text=message.replace("STATUS:", "").strip())
        else:
            text_widget.config(state="normal")
            text_widget.insert(tk.END, message)
            text_widget.config(state="disabled")
            text_widget.see(tk.END)
    if should_exit:
        root.destroy()
    else:
        root.after(100, process_gui_queue, text_widget, status_label)

# --- Assistant Core Functions ---
def speak(text):
    # Animate robot mouth and LEDs when speaking
    if "robot_state" in globals():
        robot_state["mouth_open"] = True
        robot_state["led_on"] = True
        robot_state["speaking"] = True
    update_gui(text, "Nova")
    engine = pyttsx3.init()
    # Animate waveform during speech
    import threading
    import time
    speaking_flag = [True]
    def waveform_speaking():
        while speaking_flag[0]:
            # Simulate random waveform for now
            levels = np.abs(np.random.normal(0.5, 0.2, 8))
            levels = np.clip(levels, 0, 1)
            update_waveform(levels)
            time.sleep(0.06)
        update_waveform(None)
    t = threading.Thread(target=waveform_speaking)
    t.start()
    engine.say(text)
    engine.runAndWait()
    engine.stop()
    speaking_flag[0] = False
    t.join()
    if "robot_state" in globals():
        robot_state["mouth_open"] = False
        robot_state["led_on"] = False
        robot_state["speaking"] = False

def launch_application(app_name):
    """Tries to launch an application using two methods."""
    speak(f"Trying to open {app_name}...")
    try:
        os.startfile(app_name)
        speak(f"Opening {app_name}.")
        return True
    except Exception as e:
        print(f"Direct launch for '{app_name}' failed: {e}. Trying file search next.")

    start_menu_paths = [
        os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
        os.path.join(os.environ['ALLUSERSPROFILE'], 'Microsoft', 'Windows', 'Start Menu', 'Programs')
    ]
    for path in start_menu_paths:
        for root, dirs, files in os.walk(path):
            for file in files:
                if app_name.lower() in file.lower().replace(".lnk", ""):
                    try:
                        file_path = os.path.join(root, file)
                        os.startfile(file_path)
                        speak(f"Opening {file.replace('.lnk', '')}.")
                        return True
                    except Exception as e:
                        print(f"Could not open file {file_path}: {e}")
                        continue
    return False

def listen_for_command(audio_stream):
    """Listens for a command from the main audio stream after wake word detection."""
    update_gui("Listening for command...", "STATUS")
    frames = []
    for _ in range(0, int(porcupine.sample_rate / porcupine.frame_length * 5)):
        pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
        frames.append(pcm)
    
    audio_data = b''.join(frames)
    audio_source = sr.AudioData(audio_data, porcupine.sample_rate, pa.get_sample_size(pyaudio.paInt16))
    try:
        update_gui("Recognizing...", "STATUS")
        query = recognizer.recognize_google(audio_source)
        update_gui(query, "You")
        return query.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        speak("Sorry, my speech service is down.")
        return ""

def handle_command(audio_stream):
    """This function contains all of Nova's skills, correctly ordered."""
    speak("Yes?")
    command = listen_for_command(audio_stream)
    if not command:
        speak("I didn't hear a command.")
        return

    # --- Complete and Correctly Ordered Skill Checklist ---
    if "goodbye" in command or "exit" in command:
        speak("Goodbye!")
        return "exit"

    elif "open browser" in command:
        speak("Opening Google Chrome.")
        os.startfile("chrome")

    elif "open" in command:
        app_name = command.replace("open", "").strip()
        if not launch_application(app_name):
            speak(f"Sorry, I tried everything but couldn't find or open {app_name}.")
            
    elif "search for" in command:
        search_query = command.replace("search for", "").strip()
        search_url = f"https://www.google.com/search?q={search_query}"
        speak(f"Here are the search results for {search_query}.")
        webbrowser.open(search_url)

    elif "what" in command and "time" in command:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {current_time}.")

    elif ("what" in command and "date" in command) or "today's date" in command:
        current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
        speak(f"Today's date is {current_date}.")
    
    elif "weather" in command:
        speak("The weather skill is not active. Please add a weather API key to enable it.")

    elif ("what is my" in command) or ("what's my" in command) or ("what did i tell you about" in command):
        try:
            question_phrases = ["what is my", "what's my", "what did i tell you about"]
            key_to_recall = command
            for phrase in question_phrases:
                if phrase in key_to_recall:
                    key_to_recall = key_to_recall.replace(phrase, "").strip()
            key_to_recall = key_to_recall.replace("?", "").strip()
            recall_from_memory(key_to_recall)
        except Exception as e:
            print(f"Recall error: {e}")
            speak("I had trouble accessing my memory.")

    elif "my" in command and " is " in command:
        try:
            my_index = command.find("my")
            fact_to_remember = command[my_index:]
            key, value = fact_to_remember.split(" is ", 1)
            save_to_memory(key.strip(), value.strip())
        except ValueError:
            speak("I had trouble understanding that. Please phrase it as 'my [something] is [something else]'.")
    
    else:
        update_gui("Thinking...", "STATUS")
        speak("Thinking...")
        try:
            response = model.generate_content(command)
            speak(str(response.text))
        except Exception as e:
            print(f"An error occurred: {e}")
            speak("Sorry, I had some trouble connecting to my brain.")

def main_assistant_loop():
    """The main loop for wake word detection and command handling."""
    audio_stream = None
    global pa, porcupine
    try:
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )
        update_gui("Say 'Bumblebee' to activate.", "STATUS")

        while True:
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            keyword_index = porcupine.process(pcm)

            if keyword_index >= 0:
                update_gui("Wake word detected!", "STATUS")
                if handle_command(audio_stream) == "exit":
                    break
                else:
                    update_gui("Say 'Bumblebee' to activate.", "STATUS")
    except KeyboardInterrupt:
        print("Stopping via keyboard.")
    finally:
        if 'porcupine' in locals() and porcupine is not None:
            porcupine.delete()
        if 'audio_stream' in locals() and audio_stream is not None:
            audio_stream.close()
        if 'pa' in locals() and pa is not None:
            pa.terminate()
        gui_queue.put("STATUS: Assistant stopped.")
        gui_queue.put("EXIT_GUI")

# --- GUI Setup and Main Entry Point ---
if __name__ == "__main__":
    gui_queue = Queue()

    # --- Modern Robotic GUI Theme ---
    root = tk.Tk()
    root.title("Nova Assistant")
    root.geometry("520x700")
    root.configure(bg="#181C24")

    # Custom fonts and colors
    FONT_HEADER = ("Orbitron", 20, "bold")
    FONT_BODY = ("Consolas", 12)
    FONT_STATUS = ("Consolas", 10, "italic")
    COLOR_BG = "#181C24"
    COLOR_PANEL = "#232837"
    COLOR_ACCENT = "#00FFF7"
    COLOR_TEXT = "#E6E6E6"
    COLOR_USER = "#00FFF7"
    COLOR_NOVA = "#FFB300"
    COLOR_STATUS = "#7FFFD4"

    # Try to use Orbitron font, fallback if not available
    try:
        import tkinter.font as tkFont
        tkFont.nametofont("TkDefaultFont").configure(family="Orbitron")
    except Exception:
        pass


    # Header with animated robot and title
    header_frame = tk.Frame(root, bg=COLOR_PANEL, height=110, bd=0, relief=tk.FLAT)
    header_frame.pack(fill="x", pady=(0, 8))

    # Animated robot on Canvas (with mouth, LED cheeks, facial expressions)
    robot_canvas = tk.Canvas(header_frame, width=100, height=90, bg=COLOR_PANEL, highlightthickness=0)
    robot_canvas.pack(side="left", padx=(18, 8), pady=8)

    # Draw robot body
    body = robot_canvas.create_oval(25, 40, 75, 80, fill="#222C36", outline=COLOR_ACCENT, width=2)
    head = robot_canvas.create_oval(30, 15, 70, 55, fill="#232837", outline=COLOR_ACCENT, width=2)
    # Eyes (animated)
    left_eye = robot_canvas.create_oval(42, 30, 48, 36, fill=COLOR_ACCENT, outline="", width=0)
    right_eye = robot_canvas.create_oval(52, 30, 58, 36, fill=COLOR_ACCENT, outline="", width=0)
    # Cheek LEDs
    left_led = robot_canvas.create_oval(36, 42, 41, 47, fill="#232837", outline="", width=0)
    right_led = robot_canvas.create_oval(59, 42, 64, 47, fill="#232837", outline="", width=0)
    # Antenna
    antenna = robot_canvas.create_line(50, 15, 50, 5, fill=COLOR_ACCENT, width=2)
    antenna_tip = robot_canvas.create_oval(47, 2, 53, 8, fill=COLOR_ACCENT, outline="", width=0)
    # Mouth (animated)
    mouth = robot_canvas.create_arc(45, 38, 55, 48, start=0, extent=180, style=tk.ARC, outline=COLOR_ACCENT, width=2)

    # Robot state for animation
    robot_state = {"blinking": False, "mouth_open": False, "led_on": False, "expression": "neutral", "speaking": False}

    # Animation: blink eyes, move antenna, animate mouth and LEDs
    def animate_robot(blink_state=[False], antenna_dir=[1], antenna_offset=[0], mouth_state=[False], led_state=[False]):
        # Blink eyes
        if robot_state["blinking"]:
            robot_canvas.itemconfig(left_eye, fill="#232837")
            robot_canvas.itemconfig(right_eye, fill="#232837")
        else:
            robot_canvas.itemconfig(left_eye, fill=COLOR_ACCENT)
            robot_canvas.itemconfig(right_eye, fill=COLOR_ACCENT)

        # Animate antenna tip up and down
        offset = antenna_offset[0]
        if offset > 5:
            antenna_dir[0] = -1
        elif offset < -5:
            antenna_dir[0] = 1
        antenna_offset[0] += antenna_dir[0]
        robot_canvas.move(antenna_tip, 0, antenna_dir[0])
        robot_canvas.move(antenna, 0, antenna_dir[0])

        # Animate mouth (open when speaking)
        if robot_state["mouth_open"]:
            robot_canvas.coords(mouth, 44, 38, 56, 54)
            robot_canvas.itemconfig(mouth, extent=180, start=0)
        else:
            robot_canvas.coords(mouth, 45, 38, 55, 48)
            robot_canvas.itemconfig(mouth, extent=180, start=0)

        # Animate LED cheeks (on when speaking)
        if robot_state["led_on"]:
            robot_canvas.itemconfig(left_led, fill="#00FFF7")
            robot_canvas.itemconfig(right_led, fill="#00FFF7")
        else:
            robot_canvas.itemconfig(left_led, fill="#232837")
            robot_canvas.itemconfig(right_led, fill="#232837")

        # Blink every ~2 seconds
        if not robot_state["speaking"] and not robot_state["blinking"] and (robot_canvas.after_idle):
            robot_state["blinking"] = True
            robot_canvas.after(120, lambda: robot_state.update({"blinking": False}))
        # Schedule next frame
        robot_canvas.after(400, animate_robot)

    animate_robot()

    # --- Settings Button and Panel ---
    def open_settings():
        settings_win = tk.Toplevel(root)
        settings_win.title("Settings")
        settings_win.geometry("340x320")
        settings_win.configure(bg=COLOR_PANEL)
        tk.Label(settings_win, text="Settings", font=FONT_HEADER, bg=COLOR_PANEL, fg=COLOR_ACCENT).pack(pady=10)

        # Theme selection
        tk.Label(settings_win, text="Theme:", font=FONT_BODY, bg=COLOR_PANEL, fg=COLOR_TEXT).pack(anchor="w", padx=20, pady=(10,0))
        theme_var = tk.StringVar(value="Dark")
        def set_theme():
            # Only two themes for now
            if theme_var.get() == "Dark":
                root.configure(bg="#181C24")
                main_frame.configure(bg=COLOR_PANEL)
                conversation_text.configure(bg=COLOR_BG, fg=COLOR_TEXT)
                status_label.configure(bg=COLOR_PANEL, fg=COLOR_STATUS)
            else:
                root.configure(bg="#F0F0F0")
                main_frame.configure(bg="#E0E0E0")
                conversation_text.configure(bg="#FFFFFF", fg="#222C36")
                status_label.configure(bg="#E0E0E0", fg="#222C36")
        tk.Radiobutton(settings_win, text="Dark", variable=theme_var, value="Dark", command=set_theme, bg=COLOR_PANEL, fg=COLOR_TEXT, selectcolor=COLOR_ACCENT).pack(anchor="w", padx=40)
        tk.Radiobutton(settings_win, text="Light", variable=theme_var, value="Light", command=set_theme, bg=COLOR_PANEL, fg=COLOR_TEXT, selectcolor=COLOR_ACCENT).pack(anchor="w", padx=40)

        # Voice selection
        tk.Label(settings_win, text="Voice:", font=FONT_BODY, bg=COLOR_PANEL, fg=COLOR_TEXT).pack(anchor="w", padx=20, pady=(18,0))
        voices = pyttsx3.init().getProperty('voices')
        voice_var = tk.StringVar(value=voices[0].id)
        for v in voices:
            tk.Radiobutton(settings_win, text=v.name, variable=voice_var, value=v.id, bg=COLOR_PANEL, fg=COLOR_TEXT, selectcolor=COLOR_ACCENT).pack(anchor="w", padx=40)

        # Personality selection
        tk.Label(settings_win, text="Personality:", font=FONT_BODY, bg=COLOR_PANEL, fg=COLOR_TEXT).pack(anchor="w", padx=20, pady=(18,0))
        personality_var = tk.StringVar(value="Friendly")
        for p in ["Friendly", "Formal", "Witty", "Serious"]:
            tk.Radiobutton(settings_win, text=p, variable=personality_var, value=p, bg=COLOR_PANEL, fg=COLOR_TEXT, selectcolor=COLOR_ACCENT).pack(anchor="w", padx=40)

        # Save button
        def save_settings():
            # Save theme, voice, personality to a config file or global state (for now, just print)
            print("Theme:", theme_var.get())
            print("Voice:", voice_var.get())
            print("Personality:", personality_var.get())
            settings_win.destroy()
        tk.Button(settings_win, text="Save", command=save_settings, bg=COLOR_ACCENT, fg="#232837", font=FONT_BODY).pack(pady=18)

    settings_btn = tk.Button(header_frame, text="⚙️", font=("Arial", 16), bg=COLOR_PANEL, fg=COLOR_ACCENT, bd=0, relief=tk.FLAT, activebackground=COLOR_PANEL, activeforeground=COLOR_ACCENT, command=open_settings)
    settings_btn.pack(side="right", padx=12, pady=8)

    # Main conversation panel with rounded corners effect
    main_frame = tk.Frame(root, bg=COLOR_PANEL, bd=0, relief=tk.FLAT)
    main_frame.pack(pady=(0, 10), padx=18, fill="both", expand=True)

    # Conversation text area
    conversation_text = tk.Text(
        main_frame,
        wrap="word",
        state="disabled",
        font=FONT_BODY,
        bg=COLOR_BG,
        fg=COLOR_TEXT,
        insertbackground=COLOR_ACCENT,
        bd=0,
        relief=tk.FLAT,
        highlightthickness=0,
        padx=12,
        pady=12,
    )
    conversation_text.tag_configure("user", foreground=COLOR_USER)
    conversation_text.tag_configure("nova", foreground=COLOR_NOVA)
    conversation_text.tag_configure("status", foreground=COLOR_STATUS, font=FONT_STATUS)

    # Custom scrollbar
    style_scroll = tk.Scrollbar(main_frame, command=conversation_text.yview, troughcolor=COLOR_PANEL, bg=COLOR_ACCENT, bd=0, relief=tk.FLAT)
    conversation_text.config(yscrollcommand=style_scroll.set)
    style_scroll.pack(side="right", fill="y")
    conversation_text.pack(side="left", fill="both", expand=True)

    # Status bar
    status_label = tk.Label(
        root,
        text="Initializing...",
        bd=0,
        relief=tk.FLAT,
        anchor=tk.W,
        font=FONT_STATUS,
        bg=COLOR_PANEL,
        fg=COLOR_STATUS,
        padx=10,
        pady=6,
    )
    status_label.pack(side=tk.BOTTOM, fill=tk.X)

    # --- Override update_gui to use tags for user/Nova/status ---
    def update_gui_modern(message, sender="Nova"):
        gui_queue.put((message, sender))

    # Patch the global update_gui function
    import builtins
    builtins.update_gui = update_gui_modern
    globals()["update_gui"] = update_gui_modern

    def process_gui_queue_modern(text_widget, status_label):
        should_exit = False
        while not gui_queue.empty():
            item = gui_queue.get_nowait()
            if isinstance(item, tuple):
                message, sender = item
            else:
                message, sender = item, "Nova"
            if message == "EXIT_GUI":
                should_exit = True
                continue
            if "STATUS:" in message:
                status_label.config(text=message.replace("STATUS:", "").strip())
            else:
                text_widget.config(state="normal")
                tag = "nova" if sender == "Nova" else ("user" if sender == "You" else "status")
                text_widget.insert(tk.END, f"{sender}: {message}\n", tag)
                text_widget.config(state="disabled")
                text_widget.see(tk.END)
        if should_exit:
            root.destroy()
        else:
            root.after(100, process_gui_queue_modern, text_widget, status_label)

    # --- Animated Background (Particle Effect) ---
    bg_canvas = tk.Canvas(root, width=520, height=700, bg=COLOR_BG, highlightthickness=0)
    bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
    import random
    particles = []
    for _ in range(30):
        x = random.randint(0, 520)
        y = random.randint(0, 700)
        r = random.randint(2, 5)
        dx = random.choice([-1, 1]) * random.uniform(0.2, 0.7)
        dy = random.choice([-1, 1]) * random.uniform(0.2, 0.7)
        color = COLOR_ACCENT if random.random() > 0.5 else COLOR_STATUS
        p = {'id': bg_canvas.create_oval(x, y, x+r, y+r, fill=color, outline=""), 'x': x, 'y': y, 'r': r, 'dx': dx, 'dy': dy}
        particles.append(p)
    def animate_particles():
        for p in particles:
            p['x'] += p['dx']
            p['y'] += p['dy']
            if p['x'] < 0 or p['x'] > 520:
                p['dx'] *= -1
            if p['y'] < 0 or p['y'] > 700:
                p['dy'] *= -1
            bg_canvas.move(p['id'], p['dx'], p['dy'])
        bg_canvas.after(40, animate_particles)
    animate_particles()

    # Raise all main widgets above the background
    bg_canvas.lower()
    header_frame.lift()

    # --- Voice Waveform Visualizer ---
    waveform_canvas = tk.Canvas(header_frame, width=100, height=30, bg=COLOR_PANEL, highlightthickness=0)
    waveform_canvas.pack(side="left", padx=(0, 0), pady=8)
    waveform_bars = [waveform_canvas.create_rectangle(i*10+2, 25, i*10+8, 25, fill=COLOR_ACCENT, outline="") for i in range(8)]
    import math
    def update_waveform(levels=None):
        if levels is None:
            # Idle animation
            for i, bar in enumerate(waveform_bars):
                h = 8 + 8*math.sin((i+1)+tk._default_root.winfo_pointerx()/50)
                waveform_canvas.coords(bar, i*10+2, 25-h, i*10+8, 25)
        else:
            for i, bar in enumerate(waveform_bars):
                h = 8 + 16*levels[i]
                waveform_canvas.coords(bar, i*10+2, 25-h, i*10+8, 25)
        waveform_canvas.after(60, update_waveform)
    update_waveform()

    # Start assistant thread
    assistant_thread = threading.Thread(target=main_assistant_loop, daemon=True)
    assistant_thread.start()

    process_gui_queue_modern(conversation_text, status_label)
    root.mainloop()