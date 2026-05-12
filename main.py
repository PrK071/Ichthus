import os
from db import init_db
from index import index_songs
from audio import record_audio
from recognizer import recognize

if __name__ == "__main__":
    conn = init_db()

    if not os.path.exists("SONGS"):
        os.mkdir("SONGS")
        print("Pasta 'SONGS' criada. Coloque arquivos .wav ou .mp3.")
        exit()

    try:
        if input("Deseja indexar novas músicas? (s/n): ").strip().lower() in ("s", "sim"):
            index_songs(conn)

        audio = record_audio()
        name, score = recognize(audio, conn)

        if name:
            print(f"Música reconhecida: {name}  (confiança: {score})")
        else:
            print(f"Música não reconhecida. (melhor score: {score})")
    finally:
        conn.close()
        print("Conexão com o banco de dados fechada.")
