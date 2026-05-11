import customtkinter as ctk
import threading
import os
import sounddevice as sd
from db import init_db, DB_NAME
from index import index_songs
from audio import record_audio
from recognizer import recognize


class MusicRecognizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Buscador de Músicas - Shazam Clone")
        self.geometry("500x480")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.conn = init_db()

        self.devices = sd.query_devices()
        self.input_devices = [
            f"{i}: {d['name']}"
            for i, d in enumerate(self.devices)
            if d["max_input_channels"] > 0
        ]

        self.label_title = ctk.CTkLabel(
            self, text="Music Recognizer", font=("Roboto", 24, "bold")
        )
        self.label_title.pack(pady=20)

        self.btn_recognize = ctk.CTkButton(
            self,
            text="Ouvir Música",
            command=self.start_recognition_thread,
            height=50,
            font=("Roboto", 16),
        )
        self.btn_recognize.pack(pady=10, padx=20, fill="x")

        self.btn_stop = ctk.CTkButton(
            self,
            text="Parar Gravação",
            command=self.stop_recognition,
            fg_color="#CC3333",
            hover_color="#992222",
            state="disabled",
        )
        self.btn_stop.pack(pady=5, padx=20, fill="x")

        self.label_device = ctk.CTkLabel(
            self, text="Selecione o Microfone/Entrada:", font=("Roboto", 12)
        )
        self.label_device.pack(pady=(10, 0))

        self.device_selector = ctk.CTkComboBox(
            self, values=self.input_devices, width=400
        )
        self.device_selector.pack(pady=5, padx=20)
        self.device_selector.set(self.input_devices[0] if self.input_devices else "")

        self.btn_index = ctk.CTkButton(
            self,
            text="Indexar Pasta 'songs'",
            command=self.run_indexing,
            fg_color="transparent",
            border_width=2,
        )
        self.btn_index.pack(pady=10, padx=20, fill="x")

        self.btn_reset_db = ctk.CTkButton(
            self,
            text="Resetar/Apagar Banco de Dados",
            command=self.reset_db,
            fg_color="#555555",
            hover_color="#333333",
        )
        self.btn_reset_db.pack(pady=5, padx=20, fill="x")

        self.status_label = ctk.CTkLabel(
            self, text="Pronto para ouvir", font=("Roboto", 14)
        )
        self.status_label.pack(pady=15)

        self.result_box = ctk.CTkTextbox(self, height=100, width=400)
        self.result_box.pack(pady=5, padx=20)
        self.result_box.insert("0.0", "Os resultados aparecerão aqui...")

        self.btn_clear = ctk.CTkButton(
            self,
            text="Limpar Resultados",
            command=self.clear_results,
            fg_color="gray",
            hover_color="#555555",
        )
        self.btn_clear.pack(pady=5, padx=20)

        self.label_count = ctk.CTkLabel(
            self, text="Músicas no banco: 0", font=("Roboto", 10)
        )
        self.label_count.pack(pady=5)

        self.update_song_count()

    
    #Helpers

    def update_status(self, text: str):
        self.status_label.configure(text=text)

    def clear_results(self):
        self.result_box.delete("0.0", "end")
        self.result_box.insert("0.0", "Os resultados aparecerão aqui...")

    def update_song_count(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM songs")
        count = cur.fetchone()[0]
        self.label_count.configure(text=f"Músicas no banco: {count}")

    
    #Recognition

    def start_recognition_thread(self):
        self.btn_recognize.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.update_status("Gravando áudio...")
        thread = threading.Thread(target=self.run_recognition, daemon=True)
        thread.start()

    def run_recognition(self):
        self.result_box.delete("0.0", "end")
        try:
            selection = self.device_selector.get()
            device_id = int(selection.split(":")[0]) if selection else None

            audio = record_audio(device=device_id)

            self.update_status("Analisando frequências...")
            name, score = recognize(audio, self.conn)

            self.result_box.delete("0.0", "end")
            if name:
                self.result_box.insert(
                    "0.0", f" Música Encontrada:\n{name}\n\nConfiança: {score} hashes"
                )
            else:
                msg = " Música não identificada."
                if score > 0:
                    msg += f"\n(Melhor score: {score} — tente re-indexar ou aumentar o volume)"
                self.result_box.insert("0.0", msg)

        except Exception as e:
            self.result_box.delete("0.0", "end")
            self.result_box.insert("0.0", f"Erro: {e}")
        finally:
            self.update_status("Pronto")
            self.btn_recognize.configure(state="normal")
            self.btn_stop.configure(state="disabled")

    def stop_recognition(self):
        sd.stop()
        self.update_status("Gravação interrompida.")

    #DB/Indexing

    def run_indexing(self):
        self.update_status("Indexando músicas...")
        index_songs(self.conn)
        self.update_status("Indexação concluída!")
        self.update_song_count()

    def reset_db(self):
        self.conn.close()
        try:
            if os.path.exists(DB_NAME):
                os.remove(DB_NAME)
            self.conn = init_db()
            self.update_song_count()
            self.update_status("Banco de dados resetado!")
        except Exception as e:
            self.update_status(f"Erro ao resetar: {e}")

    def on_closing(self):
        self.conn.close()
        self.destroy()


if __name__ == "__main__":
    app = MusicRecognizerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
