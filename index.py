import os
from audio import load_audio, spectrogram
from fingerprint import find_peaks, generate_hashes

SONGS_DIR = "songs"

def index_songs(conn):
    cur = conn.cursor()

    for file in os.listdir(SONGS_DIR):
        #aceita WAV e MP3 agr(comum em datasets e APIs)
        if not (file.lower().endswith(".wav") or file.lower().endswith(".mp3")):
            continue

        cur.execute("SELECT id FROM songs WHERE name = ?", (file,))
        if cur.fetchone():
            print(f"Pulando {file}, já indexada.")
            continue

        print(f"indexando {file}")
        path = os.path.join(SONGS_DIR, file)
        cur.execute("INSERT INTO songs (name) VALUES (?)", (file,))
        song_id = cur.lastrowid

        audio = load_audio(path)
        S = spectrogram(audio)
        peaks = find_peaks(S)
        hashes = generate_hashes(peaks)

        cur.executemany(
            "INSERT INTO fingerprints VALUES (?, ?, ?)",
            [(h, song_id, int(offset)) for h, offset in hashes]
        )
        conn.commit()

    print("Indexação concluída.\n")
