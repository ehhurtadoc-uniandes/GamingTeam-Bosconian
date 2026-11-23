"""Genera los efectos y la música del juego (#38) como archivos OGG originales.

Los sonidos se sintetizan aquí con ondas cuadradas, triangulares y ruido, al estilo de los
juegos de 8 bits, y ffmpeg los convierte a OGG (el formato que funciona en la web con pygbag).
No se usa ningún sonido del juego original.

Uso (desde la raíz del repositorio, con ffmpeg en el PATH):
    python tools/generate_audio.py
"""
import math
import os
import random
import struct
import subprocess
import tempfile
import wave

RATE = 22050
SND_DIR = os.path.join("assets", "snd")
MUSIC_DIR = os.path.join("assets", "music")


# ---------------------------------------------------------------- ondas y envolventes

def midi_freq(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def square(phase: float, duty: float = 0.5) -> float:
    return 1.0 if phase % 1.0 < duty else -1.0


def triangle(phase: float) -> float:
    p = phase % 1.0
    return 4 * p - 1 if p < 0.5 else 3 - 4 * p


def envelope(t: float, length: float, attack: float = 0.005, release: float = 0.03) -> float:
    """Sube en attack, se mantiene y baja en release al final de la nota."""
    if t < attack:
        return t / attack
    if t > length - release:
        return max(0.0, (length - t) / release)
    return 1.0


def tone(freq_start: float, freq_end: float, length: float, wave_fn=square, volume: float = 0.5,
         decay: float = 0.0) -> list[float]:
    """Tono con barrido de frecuencia de freq_start a freq_end y caída exponencial opcional."""
    samples = []
    phase = 0.0
    total = int(length * RATE)
    for i in range(total):
        t = i / RATE
        freq = freq_start + (freq_end - freq_start) * i / total
        phase += freq / RATE
        amp = volume * envelope(t, length) * math.exp(-decay * t)
        samples.append(amp * wave_fn(phase))
    return samples


def noise(length: float, volume: float = 0.6, decay: float = 6.0, hold_start: int = 1,
          hold_end: int = 1, seed: int = 1) -> list[float]:
    """Ruido que se repite hold muestras: con hold alto suena más grave (estruendo)."""
    rng = random.Random(seed)
    samples = []
    total = int(length * RATE)
    value = 0.0
    counter = 0
    for i in range(total):
        hold = round(hold_start + (hold_end - hold_start) * i / total)
        if counter <= 0:
            value = rng.uniform(-1, 1)
            counter = max(1, hold)
        counter -= 1
        t = i / RATE
        samples.append(volume * value * math.exp(-decay * t) * envelope(t, length, 0.002, 0.02))
    return samples


def silence(length: float) -> list[float]:
    return [0.0] * int(length * RATE)


def mix(*tracks: list[float]) -> list[float]:
    length = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(length)]


def concat(*parts: list[float]) -> list[float]:
    return [s for part in parts for s in part]


# ---------------------------------------------------------------- secuencias musicales

def voice(notes: list[tuple[int | None, float]], beat: float, wave_fn, volume: float,
          gate: float = 0.85) -> list[float]:
    """Una voz: lista de (nota MIDI o None para silencio, duración en pulsos)."""
    out: list[float] = []
    for note, beats in notes:
        length = beats * beat
        sounding = length * gate
        if note is None:
            out += silence(length)
        else:
            out += tone(midi_freq(note), midi_freq(note), sounding, wave_fn, volume)
            out += silence(length - sounding)
    return out


def drums(pattern: str, beat: float, volume: float = 0.25) -> list[float]:
    """Batería de ruido: K bombo, S caja, h platillo, . silencio; cada carácter es medio pulso."""
    step = beat / 2
    out: list[float] = []
    for i, hit in enumerate(pattern):
        if hit == "K":
            part = mix(tone(150, 50, step, triangle, volume * 2.2, decay=18), silence(step))
        elif hit == "S":
            part = noise(step, volume, decay=22, hold_start=2, hold_end=2, seed=i)
        elif hit == "h":
            part = noise(step, volume * 0.45, decay=60, seed=i)
        else:
            part = silence(step)
        out += part[:int(step * RATE)] + silence(step)[len(part):]
    return out


def arpeggio(chords: list[list[int]], beats_per_chord: int, octave: int = 0) -> list[tuple[int, float]]:
    """Arpegio en corcheas que recorre las notas de cada acorde."""
    notes = []
    for chord in chords:
        pattern = chord + chord[1:-1][::-1]
        for i in range(beats_per_chord * 2):
            notes.append((pattern[i % len(pattern)] + 12 * octave, 0.5))
    return notes


def bass_line(roots: list[int], beats_per_chord: int, style: str = "eighths") -> list[tuple[int, float]]:
    notes = []
    for root in roots:
        if style == "eighths":
            notes += [(root, 0.5), (root + 12, 0.5)] * beats_per_chord
        else:
            notes += [(root, 1.0)] * beats_per_chord
    return notes


def song(beat: float, *voices_info) -> list[float]:
    return mix(*[voice(notes, beat, wave_fn, volume) for notes, wave_fn, volume in voices_info])


# Acordes como notas MIDI (60 = do central).
AM, F, C, G = [57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]
DM, BB, EM = [50, 53, 57], [46, 50, 53], [52, 55, 59]


def music_title() -> list[float]:
    beat = 60 / 112
    chords = [AM, F, C, G] * 2
    melody = [(76, 1.5), (74, 0.5), (72, 1), (69, 1),
              (72, 1.5), (74, 0.5), (77, 2),
              (79, 1.5), (77, 0.5), (76, 1), (72, 1),
              (74, 3), (None, 1),
              (76, 1.5), (74, 0.5), (72, 1), (69, 1),
              (72, 1), (74, 1), (77, 1), (81, 1),
              (79, 1.5), (77, 0.5), (76, 1), (74, 1),
              (69, 3), (None, 1)]
    return song(beat,
                (melody, lambda p: square(p, 0.25), 0.16),
                (arpeggio(chords, 4), triangle, 0.14),
                (bass_line([45, 41, 36, 43] * 2, 4, "quarters"), triangle, 0.22))


def music_play(key: int, tempo: int, seed: int) -> list[float]:
    """Pista de juego: bajo en corcheas, arpegio y una melodía corta que cambia con seed."""
    beat = 60 / tempo
    progressions = [[0, -4, -7, -2], [0, 3, -2, -4], [0, -2, -4, -5]]
    roots = [key + step for step in progressions[seed % 3]] * 2
    chords = [[r + 12, r + 15 + (seed % 2), r + 19] for r in roots]
    rng = random.Random(seed)
    scale = [0, 2, 3, 5, 7, 8, 10, 12]
    melody = []
    for r in roots:
        for _ in range(4):
            if rng.random() < 0.2:
                melody.append((None, 1))
            else:
                melody.append((r + 24 + rng.choice(scale), rng.choice([0.5, 1, 1])))
                if melody[-1][1] == 0.5:
                    melody.append((r + 24 + rng.choice(scale), 0.5))
    pattern = "K.h.S.h.K.K.S.h." * len(roots)
    return mix(song(beat,
                    (melody, lambda p: square(p, 0.5), 0.12),
                    (arpeggio(chords, 4), lambda p: square(p, 0.125), 0.07),
                    (bass_line(roots, 4), triangle, 0.24)),
               drums(pattern, beat, 0.16))


def music_victory() -> list[float]:
    beat = 60 / 132
    melody = [(72, 0.5), (72, 0.5), (72, 0.5), (76, 1.5), (79, 1), (84, 2), (None, 2),
              (81, 1), (79, 1), (77, 1), (76, 1), (74, 1), (76, 1), (72, 2)]
    chords = [C, F, G, C]
    return song(beat,
                (melody, lambda p: square(p, 0.25), 0.16),
                (arpeggio(chords, 4), triangle, 0.14),
                (bass_line([36, 41, 43, 36], 4, "quarters"), triangle, 0.22))


def music_defeat() -> list[float]:
    beat = 60 / 72
    melody = [(69, 2), (67, 1), (65, 1), (64, 2), (62, 2), (65, 2), (64, 1), (62, 1), (61, 4)]
    return song(beat,
                (melody, lambda p: square(p, 0.5), 0.13),
                (bass_line([45, 41, 38, 45], 4, "quarters"), triangle, 0.22))


# ---------------------------------------------------------------- efectos

def effects() -> dict[str, list[float]]:
    def notes(seq, length, wave_fn=square, volume=0.35):
        return concat(*[tone(midi_freq(n), midi_freq(n), length, wave_fn, volume) for n in seq])

    return {
        "player_fire": tone(1400, 350, 0.08, lambda p: square(p, 0.25), 0.3, decay=20),
        "explosion": noise(0.35, 0.7, decay=9, hold_start=3, hold_end=10, seed=2),
        "player_explosion": mix(noise(1.2, 0.75, decay=3, hold_start=4, hold_end=24, seed=3),
                                tone(220, 40, 1.2, triangle, 0.4, decay=2.5)),
        "base_destroyed": mix(noise(0.9, 0.7, decay=4, hold_start=2, hold_end=16, seed=4),
                              tone(880, 110, 0.6, square, 0.2, decay=4)),
        "extra_life": notes([72, 76, 79, 84, 79, 84], 0.07, volume=0.3),
        "menu_move": tone(880, 880, 0.04, square, 0.22),
        "menu_accept": notes([76, 83], 0.06, volume=0.25),
        "pause": notes([83, 76], 0.07, volume=0.25),
        "level_clear": notes([67, 71, 74, 79, 74, 79, 83], 0.09, volume=0.28),
        "alert_green": notes([72, 79], 0.12, triangle, 0.4),
        "alert_yellow": concat(*[concat(tone(988, 988, 0.08, square, 0.25), silence(0.06)) for _ in range(3)]),
        "alert_red": concat(*[concat(tone(600, 1200, 0.25, square, 0.22), tone(1200, 600, 0.25, square, 0.22))
                              for _ in range(2)]),
    }


# ---------------------------------------------------------------- escritura

def write_ogg(samples: list[float], path: str) -> None:
    peak = max(1e-6, max(abs(s) for s in samples))
    scale = min(1.0, 0.9 / peak)
    data = b"".join(struct.pack("<h", int(max(-1, min(1, s * scale)) * 32767)) for s in samples)
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "audio.wav")
        with wave.open(wav_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(data)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path, "-c:a", "libvorbis",
                        "-q:a", "3", path], check=True)
    print(path)


def main() -> None:
    os.makedirs(SND_DIR, exist_ok=True)
    os.makedirs(MUSIC_DIR, exist_ok=True)
    for name, samples in effects().items():
        write_ogg(samples, os.path.join(SND_DIR, f"{name}.ogg"))
    music = {
        "title": music_title(),
        "play_1": music_play(45, 140, 1),
        "play_2": music_play(50, 150, 2),
        "play_3": music_play(43, 160, 3),
        "victory": music_victory(),
        "defeat": music_defeat(),
    }
    for name, samples in music.items():
        write_ogg(samples, os.path.join(MUSIC_DIR, f"{name}.ogg"))


if __name__ == "__main__":
    main()
