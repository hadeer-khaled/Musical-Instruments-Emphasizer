from pathlib import Path
from tkinter import Tk, ttk, Canvas, Scale, HORIZONTAL, PhotoImage, Button, IntVar
from tkinter.constants import DISABLED, FLAT, GROOVE, RAISED, RIDGE, SOLID, SUNKEN
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from scipy.fft import fft, ifft
import numpy as np
from numpy.core.shape_base import block
import sounddevice as sd
import math
import pygame
from scipy.io.wavfile import read, write
from PIL import ImageTk, Image
from tkinter.filedialog import askopenfilename
import wave
import pyaudio
import threading
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import math
import logging
from functools import partial

# initiations
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s')
pygame.init()
pygame.mixer.init()

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path("./assets")
cont = 0
music = None
music_backup = None


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


piano_sample_rate = 44100  # Hz
guitar_sample_rate = 20000  # Hz
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))

# Get current volume
current_volume = volume.GetMasterVolumeLevel()
print(current_volume)
current_song = []
fs = 0


# ------------------Start of Equalizer Part----------------------#

# define callback
def callback(in_data, frame_count, time_info, status):
    global music_wave
    data = music_wave.readframes(frame_count)
    return data, pyaudio.paContinue


def import_music():
    global music, music_wave, fs, plot, sound, cont, smoothing, ch_rang_out, ch_rang_in, music_min, music_max, music_backup
    music_path = askopenfilename()
    fs, music = read(music_path)
    music_backup = music
    logging.info(
        f'The user has imported a wav file with sampling frequency = {fs} and duration = {music.shape[0] / fs}')
    music_wave = wave.open(music_path)
    sound = threading.Thread(target=play_music)
    cont = 1
    smoothing = 0.1
    ch_rang_out = int(fs * smoothing)
    ch_rang_in = 0
    if len(music.shape) == 2:  ##if the file is stereo ,, make it mono ,,eg : one channel
        music = music[:, 1]
        music_backup = music_backup[:, 1]
    else:
        music = music[:]
        music_backup = music_backup[:]

    music_min = min(music)
    music_max = max(music)
    plot = threading.Thread(target=looping)
    spec_ch.cla()
    spec_ch.specgram(music, Fs=fs, NFFT=140)
    spec_ch.axis('off')
    graph_spec.draw()
    looping()
    sound.start()


def update_volume(self):
    global volume_level, currentVolumeDb

    # Get default audio device using PyCAW
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    # Get current volume
    currentVolumeDb = volume.GetMasterVolumeLevel()
    volume.SetMasterVolumeLevel(0.6525 * volume_level.get() - 65.25, None)

    # NOTE: -6.0 dB = half volume !
    logging.info(f'The volume currently is {volume} dB')


def looping():
    global ch_rang_in, ch_rang_out, smoothing, music, fs, cont, Main_graph, graph, music_min, music_max

    if ch_rang_out < len(music) and cont == 1:
        Main_graph.cla()

        Main_graph.set_ylim([music_min, music_max])
        Main_graph.plot(music[ch_rang_in:ch_rang_out])
        ch_rang_in += int(fs * smoothing)
        ch_rang_out += int(fs * smoothing)

    graph.draw()
    root.after(int(1000 * smoothing), looping)  # run itself again after 1000 ms


def play_pause():
    global stream, cont
    if stream.is_stopped():  # time to play audio
        stream.start_stream()
        logging.info(f'The user resumed.')

    elif stream.is_active():  # time to pause audio
        stream.stop_stream()
        logging.info(f'The user paused.')

    if not cont:
        cont = True

    else:
        cont = False


def play_music():
    global stream
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(music_wave.getsampwidth()),
                    channels=music_wave.getnchannels(),
                    rate=music_wave.getframerate(),
                    output=True,
                    stream_callback=callback)

    # start the stream
    stream.start_stream()


def equalize(self):
    global music, fs, music_wave, stream, ch_range_in, ch_range_out, fs, music_backup, eq_1, eq_2, eq_3
    fourier = np.fft.rfft(music_backup)
    freq = np.fft.rfftfreq(len(music_backup), 1 / fs)
    frequencies = [0, 400, 3000, 12000]
    eq_vals = [eq_1.get(),eq_3.get(),eq_2.get()]
    len_arr = len(fourier)
    mask = np.ones(len_arr)
    for i in range(0, len(frequencies)-1):
        mask[int(frequencies[i] * len_arr / 22050): int(frequencies[i+1] * len_arr / 22050)] = eq_vals[i]
    fourier = np.multiply(mask, fourier).tolist()

    fourier_inverse = np.fft.irfft(fourier)
    fourier_inverse = fourier_inverse.astype(music.dtype)
    write('smaller.wav', fs, fourier_inverse)
    music_wave = wave.open('smaller.wav')
    fs, music = read('smaller.wav')
    spec_ch.cla()
    spec_ch.specgram(music, Fs=fs, NFFT=140)
    graph_spec.draw()
    stream.close()
    ch_rang_out = int(fs * smoothing)
    ch_rang_in = 0
    sound = threading.Thread(target=play_music)
    sound.start()


# ------------------End of Equalizer Part----------------------#


# ------------------Start of Virtual Instruments Part----------------------#


# -----------------Start of Piano Functions------------------#

def get_wave(freq, duration=0.3):
    amplitude = 16300
    t = np.linspace(0, duration, int(piano_sample_rate * duration))

    wave = amplitude * np.sin(4 * np.pi * freq * t) * np.exp(-0.001 * 2 * np.pi * freq * t)
    wave += -1.0 / 4 * np.sin(3 * np.pi * freq * t) + 1.0 / 4 * np.sin(np.pi * freq * t) + math.sqrt(3) / 2.0 * np.cos(
        np.pi * freq * t)

    return wave.astype(np.int16)


def get_piano_notes(key):
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B', 'C1', 'C#1', 'D1', 'D#1', 'E1', 'F1']
    base_freq = 261.63  # frequency of C4 in hz

    key_freq = base_freq * pow(2, (keys.index(key) / 12))

    return key_freq


def play_note(note_wave):
    sd.play(note_wave, 44100, blocking=True)


def piano_note(mynote):
    key_freq = get_piano_notes(mynote)
    sound_wave = get_wave(key_freq)
    play_note(sound_wave)


# -----------------End of Piano Functions---------------#


# -----------------Start of Guitar Functions---------------#
def karplus_strong(wavetable, n_samples):
    """Synthesizes a new waveform from an existing wavetable, modifies last sample by averaging."""
    samples = []
    current_sample = 0
    previous_value = 0
    while len(samples) < n_samples:
        wavetable[current_sample] = 0.5 * (wavetable[current_sample] + previous_value)
        samples.append(wavetable[current_sample])
        previous_value = samples[-1]
        current_sample += 1
        current_sample = current_sample % wavetable.size
    return np.array(samples)


def create_wavetable(freq):
    global guitar_sample_rate
    wavetable_size = guitar_sample_rate // freq
    wavetable = (2 * np.random.randint(0, 2, wavetable_size) - 1).astype(np.float)
    return wavetable


def guitar_chord(freq):
    wavetable = create_wavetable(freq)
    wave = karplus_strong(wavetable, 1 * guitar_sample_rate)
    sd.play(wave, guitar_sample_rate, blocking=True)


# ------------End of Guitar Functions-------------#


# ------------Start of Drum Functions-------------#

def play_drum(gain):
    t = np.linspace(0, 0.5, int(piano_sample_rate * 0.5))
    f = (2000 + gain * 1000) * np.exp(-24 * t)
    y = np.sin(f * t)
    sd.play(y, piano_sample_rate, blocking=True)


def play_drum_center():
    play_drum(1)


def play_drum_sides():
    play_drum(0)


# ------------End of Drum Functions-------------#

# ------------------End of Virtual Instruments Part----------------------#


# ---------------------------GUI-----------------------------------------#
root = Tk()
root.geometry("1290x650")  # 1290-960 = 330

root.title("Songs Equalizer")
root.configure(bg="#AAD0D8")

notebook = ttk.Notebook(root, height=963, width=650)
window = ttk.Frame(notebook)
instruments = ttk.Frame(notebook)

notebook.add(window, text='Music Equalizer')
notebook.add(instruments, text='Virtual Insturments')

notebook.grid(row=0, column=0)

canvas = Canvas(window, bg="#AAD0D8", height=660, width=1290, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

# ------ instruments Icons --------#
piano = PhotoImage(file=relative_to_assets("piano2.png"))
canvas.create_image(910, 400, image=piano)
guitar = PhotoImage(file=relative_to_assets("guitar.png"))
canvas.create_image(1010, 400, image=guitar)
flute = PhotoImage(file=relative_to_assets("flute.png"))
canvas.create_image(1110, 400, image=flute)
vol = PhotoImage(file=relative_to_assets("v2.png"))
canvas.create_image(700 + 105 + 25, 40, image=vol)

left_canvas = Canvas(window, bg="#396EB0", height=660, width=720, bd=0, highlightthickness=0, relief="ridge")
left_canvas.place(x=0, y=0)

canvas = Canvas(instruments, bg="#AAD0D8", height=650, width=963, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)


def conf(event):
    notebook.config(height=root.winfo_height(), width=root.winfo_width())
    notebook_2.config(height=root.winfo_height(), width=root.winfo_width())


# tab 1
# ------ instruments Sliders --------#

# text color
fg = "#000000"
# color outside the trough
bg = "#AAD0D8"
troughcolor = "#396EB0"

relief = "flat"
bd = 0
width = 60

eq_1 = IntVar()
eq_1.set(1)

instrument_1 = Scale(window, from_=10, bg=bg, to=0, variable=eq_1, resolution=0.5, orient="vertical",
                     width=15, relief=relief, troughcolor=troughcolor, highlightcolor="#79B4B7", fg=fg, length=200,
                     highlightthickness=0)
instrument_1.place(x=720 + 165, y=110, width=width, height=250)
instrument_1.bind("<ButtonRelease-1>", equalize)

eq_2 = IntVar()
eq_2.set(1)

instrument_2 = Scale(window, from_=10, bg=bg, to=0, variable=eq_2, resolution=0.5, orient="vertical",
                     width=15, relief=relief, troughcolor=troughcolor, highlightcolor="#79B4B7", fg=fg, length=200,
                     highlightthickness=0)
instrument_2.place(x=720 + 165 + 60 + 40, y=110, width=width, height=250)
instrument_2.bind("<ButtonRelease-1>", equalize)

eq_3 = IntVar()
eq_3.set(1)

instrument_3 = Scale(window, from_=10, bg=bg, to=0, variable=eq_3, resolution=0.5, orient="vertical",
                     width=15, relief=relief, troughcolor=troughcolor, highlightcolor="#79B4B7", fg=fg, length=200,
                     highlightthickness=0)
instrument_3.place(x=720 + 165 + 120 + 80, y=110, width=width, height=250)
instrument_3.bind("<ButtonRelease-1>", equalize)

volume_level = IntVar()

volume = Scale(window, from_=0, bg=bg, to=100, troughcolor=troughcolor, fg=fg, length=200, variable=volume_level,
               orient=HORIZONTAL, relief=relief,
               highlightthickness=0, command=update_volume)
volume.place(x=700 + 105 + 60, y=15, width=280, height=40)
volume_level.set((100 / 65.25) * current_volume + 100)
# ------ Figures --------#
fig = Figure(figsize=(5.6, 3.7))
Main_graph = fig.add_subplot(111)
graph = FigureCanvasTkAgg(fig, master=window)
Main_graph.axis('off')
h = graph.get_tk_widget().place(x=10, y=10, width=500 + 200, height=300)

spec = Figure(figsize=(5.6, 3.7))
spec_ch = spec.add_subplot(111)
spec_ch.axis('off')
graph_spec = FigureCanvasTkAgg(spec, master=window)
s = graph_spec.get_tk_widget().place(x=10, y=320, width=500 + 200, height=300)

# ------ Buttons --------#
button_image_2 = PhotoImage(file=relative_to_assets("button_2.png"))
pause_button = Button(window, image=button_image_2, borderwidth=0, highlightthickness=0, activebackground="#AAD0D9",
                      command=play_pause, relief="flat")
pause_button.place(x=600 + 310, y=562.0, width=214.0, height=52.0)

button_image_1 = PhotoImage(file=relative_to_assets("button_1.png"))
load_button = Button(window, image=button_image_1, borderwidth=0, highlightthickness=0, command=import_music,
                     relief="flat")
load_button.place(x=840 + 330, y=555.0, width=98.0, height=67.0)

# tab2
notebook_2 = ttk.Notebook(instruments, style='right.TNotebook')

f1 = ttk.Frame(notebook_2, width=200, height=200)
f2 = ttk.Frame(notebook_2, width=200, height=200)
f3 = ttk.Frame(notebook_2, width=200, height=200)

canvas = Canvas(f1, bg="#f0f0f0", height=650, width=963, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

canvas = Canvas(f2, bg="#f0f0f0", height=650, width=963, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

canvas = Canvas(f3, bg="#f0f0f0", height=650, width=963, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

notebook_2.add(f1, text='Piano')
notebook_2.add(f2, text='Guitar')
notebook_2.add(f3, text='Drum')

notebook_2.grid(row=0, column=0, sticky="nw")

# -----------------Piano--------------------#
img1 = ImageTk.PhotoImage(Image.open(relative_to_assets("piano.jpg")))
canvas1 = Canvas(f1, width=963, height=900)
canvas1.pack()
canvas1.create_image(480, 300, image=img1, anchor='c')

# =============black keys=========================#
heights = [6, 6, 6, 6, 6, 6, 6, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
widths = [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
texts = ["C# ", "D# ", "F# ", "G# ", "A# ", "C#1", "D#1", "C", "D", "E", "F", "G", "A", "B", "C1", "D1", "E1"]
x = [270, 325, 400, 455, 510, 583, 643, 247, 292, 338, 387, 433, 478, 524, 572, 618, 668]
y = [270, 270, 270, 270, 270, 268, 268, 420, 420, 420, 420, 420, 420, 420, 420, 420, 420]
colors_fg = ["white", "white", "white", "white", "white", "white", "white", "black", "black", "black", "black", "black",
             "black", "black", "black", "black", "black"]
colors_bg = ["black", "black", "black", "black", "black", "black", "black", "white", "white", "white", "white", "white",
             "white", "white", "white", "white", "white"]
no_of_buttons_piano = len(heights)
for i in range(no_of_buttons_piano):
    button = Button(f1, height=heights[i], width=widths[i], bd=0, text=texts[i], bg=colors_bg[i], fg=colors_fg[i],
                    font=('arial', 18, 'bold'),
                    command=partial(piano_note, texts[i]))
    canvas1.create_window(x[i], y[i], anchor='w', window=button)

# # -----------------Piano--------------------#
#
#
# # -----------------Guitar--------------------#
img2 = ImageTk.PhotoImage(Image.open(relative_to_assets("guitar6.jpeg")))
canvas2 = Canvas(f2, width=963, height=900)
canvas2.pack()
canvas2.create_image(480, 300, image=img2, anchor='c')
x_guitar = [398, 427, 457, 491, 521, 551]
y_guitar = [395, 360, 390, 420, 450, 480]
freqz = [82, 110, 147, 196, 247, 330]
no_of_buttons_guitar = len(x_guitar)
for i in range(no_of_buttons_guitar):
    button = Button(f2, height=100, width=0, bd=0, text="", bg="#f5f0ea", activebackground="yellow",
                    command=partial(guitar_chord, freqz[i]))
    canvas2.create_window(x_guitar[i], y_guitar[i], anchor='w', window=button)

# ---------------Guitar--------------#

# ---------------Bongos--------------#
img3 = ImageTk.PhotoImage(Image.open(relative_to_assets("drums.jpg")))
canvas3 = Canvas(f3, width=1290, height=660)
canvas3.place(x=10, y=10)
canvas3.create_image(500, 300, image=img3, anchor='c')

button_image_drum1 = PhotoImage(file=relative_to_assets("db1.png"))
drum_btn1 = Button(f3, image=button_image_drum1, command=play_drum_center, borderwidth=0, highlightthickness=0,
                   activebackground="#AAD0D9", relief="flat")
drum_btn1.place(x=456, y=150.0, width=197, height=320)

button_image_drum2 = PhotoImage(file=relative_to_assets("db2.png"))
drum_btn2 = Button(f3, image=button_image_drum2, command=play_drum_sides, borderwidth=0, highlightthickness=0,
                   activebackground="#AAD0D9", relief="flat")
drum_btn2.place(x=400, y=230.0, width=50, height=220)

button_image_drum3 = PhotoImage(file=relative_to_assets("db3.png"))
drum_btn3 = Button(f3, image=button_image_drum3, command=play_drum_sides, borderwidth=0, highlightthickness=0,
                   activebackground="#AAD0D9", relief="flat")
drum_btn3.place(x=456 + 197 + 5, y=150.0, width=60, height=270)

# -----------Bongos--------------#


root.bind("<Configure>", conf)
root.mainloop()
