import customtkinter as ctk
import threading
import sounddevice as sd
from audio import record_audio
from API_audd import recognize_from_audio, format_result


class MusicRecognizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Music Recognizer")
        self.geometry("500x380")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

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
            self, text="Selecione o Microfone:", font=("Roboto", 12)
        )
        self.label_device.pack(pady=(10, 0))

        self.device_selector = ctk.CTkComboBox(
            self, values=self.input_devices, width=400
        )
        self.device_selector.pack(pady=5, padx=20)
        self.device_selector.set(self.input_devices[0] if self.input_devices else "")

        self.status_label = ctk.CTkLabel(
            self, text="Pronto para ouvir", font=("Roboto", 14)
        )
        self.status_label.pack(pady=15)

        self.result_box = ctk.CTkTextbox(self, height=120, width=400)
        self.result_box.pack(pady=5, padx=20)
        self.result_box.insert("0.0", "O resultado aparecerá aqui...")

        self.btn_clear = ctk.CTkButton(
            self,
            text="Limpar",
            command=self.clear_results,
            fg_color="gray",
            hover_color="#555555",
        )
        self.btn_clear.pack(pady=5, padx=20)

    def update_status(self, text: str):
        self.status_label.configure(text=text)

    def clear_results(self):
        self.result_box.delete("0.0", "end")
        self.result_box.insert("0.0", "O resultado aparecerá aqui...")

    def start_recognition_thread(self):
        self.btn_recognize.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.update_status("Ouvindo...")
        thread = threading.Thread(target=self.run_recognition, daemon=True)
        thread.start()

    def run_recognition(self):
        self.result_box.delete("0.0", "end")
        try:
            selection = self.device_selector.get()
            device_id = int(selection.split(":")[0]) if selection else None

            audio = record_audio(device=device_id)

            self.update_status("Identificando...")
            result = recognize_from_audio(audio)

            self.result_box.delete("0.0", "end")
            self.result_box.insert("0.0", format_result(result))

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

    def on_closing(self):
        self.destroy()


if __name__ == "__main__":
    app = MusicRecognizerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
