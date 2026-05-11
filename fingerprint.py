import hashlib
import numpy as np
from scipy.ndimage import maximum_filter


FAN_OUT = 15


PEAK_THRESHOLD_DB = -40.0

FREQ_NEIGHBORHOOD = 10
TIME_NEIGHBORHOOD = 10


MIN_FREQ_BIN = 10
MAX_FREQ_BIN = 300


MIN_DT = 1
MAX_DT = 200


def find_peaks(S_db: np.ndarray) -> list[tuple[int, int]]:
    
    local_max = maximum_filter(S_db, size=(FREQ_NEIGHBORHOOD, TIME_NEIGHBORHOOD)) == S_db

    
    above_threshold = S_db > PEAK_THRESHOLD_DB

    freq_mask = np.zeros(S_db.shape[0], dtype=bool)
    freq_mask[MIN_FREQ_BIN:MAX_FREQ_BIN] = True

    combined = local_max & above_threshold & freq_mask[:, np.newaxis]

    freq_indices, time_indices = np.where(combined)
    peaks = list(zip(freq_indices.tolist(), time_indices.tolist()))

    return peaks


def generate_hashes(peaks: list[tuple[int, int]]) -> list[tuple[str, int]]:
    
    peaks.sort(key=lambda x: x[1])

    hashes = []
    n = len(peaks)

    for i in range(n):
        f1, t1 = peaks[i]
        for j in range(1, FAN_OUT + 1):
            if i + j >= n:
                break
            f2, t2 = peaks[i + j]
            dt = t2 - t1
            if dt < MIN_DT:
                continue
            if dt > MAX_DT:
                
                break

            raw = f"{f1}|{f2}|{dt}".encode()
            h = hashlib.sha1(raw).hexdigest()[:20]
            hashes.append((h, t1))

    return hashes
