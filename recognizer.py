from collections import defaultdict
from audio import spectrogram
from fingerprint import find_peaks, generate_hashes

MIN_ALIGNED_MATCHES = 5

BATCH_SIZE = 900  


def recognize(audio, conn) -> tuple[str | None, int]:
    
    S_db = spectrogram(audio)
    peaks = find_peaks(S_db)

    if not peaks:
        print("[RECOGNIZER] Nenhum pico encontrado no espectrograma.")
        return None, 0

    hashes = generate_hashes(peaks)

    if not hashes:
        print("[RECOGNIZER] Nenhum hash gerado.")
        return None, 0

    print(f"[RECOGNIZER] {len(peaks)} picos, {len(hashes)} hashes gerados.")

    cur = conn.cursor()

    
    hash_to_local_offsets: dict[str, list[int]] = defaultdict(list)
    for h, offset in hashes:
        hash_to_local_offsets[h].append(int(offset))

    h_list = list(hash_to_local_offsets.keys())

    
    song_delta_hist: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    for i in range(0, len(h_list), BATCH_SIZE):
        batch = h_list[i : i + BATCH_SIZE]
        placeholders = ",".join(["?"] * len(batch))
        query = (
            f"SELECT hash, song_id, offset FROM fingerprints "
            f"WHERE hash IN ({placeholders})"
        )
        cur.execute(query, batch)

        for h, song_id, db_offset in cur.fetchall():
            
            if isinstance(db_offset, bytes):
                db_offset_val = int.from_bytes(db_offset, "little")
            else:
                db_offset_val = int(db_offset)

            for local_offset in hash_to_local_offsets[h]:
                delta = db_offset_val - local_offset
                song_delta_hist[song_id][delta] += 1

    if not song_delta_hist:
        print("[RECOGNIZER] Nenhum hash casou com o banco de dados.")
        return None, 0

    
    best_song_id = None
    best_score = 0

    for song_id, delta_hist in song_delta_hist.items():
        peak_count = max(delta_hist.values())
        if peak_count > best_score:
            best_score = peak_count
            best_song_id = song_id

    print(f"[RECOGNIZER] Melhor score: {best_score} hashes alinhados.")

    if best_score < MIN_ALIGNED_MATCHES:
        print(f"[RECOGNIZER] Score abaixo do mínimo ({MIN_ALIGNED_MATCHES}). Não reconhecido.")
        return None, best_score

    cur.execute("SELECT name FROM songs WHERE id = ?", (best_song_id,))
    row = cur.fetchone()

    if row:
        return row[0], best_score

    return None, 0
