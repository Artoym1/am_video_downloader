import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
import threading
import queue
import os
import sys
import yt_dlp
import webbrowser

# ===== Информация о программе =====
APP_NAME = "AM Video Downloader"
APP_VERSION = "1.1"
APP_AUTHOR = "Артем Моисеев, 2026 г." 
APP_EMAIL = "moisar@yandex.ru"
APP_DESCRIPTION = (
    "Программа для скачивания видео с VK Video и других сайтов,\n"
    "поддерживаемых yt-dlp (YouTube, Rutube, Ok.ru и др.).\n\n"
    "Возможности:\n"
    "  • Вставка ссылки из буфера обмена (в т.ч. правой кнопкой мыши)\n"
    "  • Выбор качества видео (до 1080p)\n"
    "  • Пауза и остановка скачивания\n"
    "  • Индикатор прогресса\n"
    "  • Полностью русский интерфейс\n\n"
    "Работает на Windows 7 x64 и выше."
)


class AMVideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("650x340")
        self.root.resizable(False, False)

        # Переменные состояния
        self.queue = queue.Queue()
        self.downloading = False
        self.paused = False
        self.stop_requested = False
        self.pause_event = threading.Event()
        self.pause_event.set()

        # --- Строка меню ---
        self._create_menu()

    
        # --- Элементы интерфейса ---
        tk.Label(root, text="Ссылка на видео:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.url_entry = tk.Entry(root, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="we")
        self._create_context_menu()

        self.paste_btn = tk.Button(root, text="Вставить URL", command=self.paste_url)
        self.paste_btn.grid(row=0, column=2, padx=5, pady=10)

        self.folder_label = tk.Label(root, text="Папка не выбрана", fg="gray")
        self.folder_label.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.choose_folder_btn = tk.Button(root, text="Выбрать папку", command=self.choose_folder)
        self.choose_folder_btn.grid(row=1, column=2, padx=5, pady=5)

        tk.Label(root, text="Качество:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.quality_var = tk.StringVar(value="Лучшее")
        self.quality_combo = ttk.Combobox(root, textvariable=self.quality_var, state="readonly",
                                          values=["Лучшее", "1080p", "720p", "480p", "360p"])
        self.quality_combo.grid(row=2, column=1, padx=5, pady=5, sticky="we")

        self.download_btn = tk.Button(root, text="Скачать", command=self.start_download,
                                      bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.download_btn.grid(row=3, column=0, padx=10, pady=10, sticky="we")

        self.pause_btn = tk.Button(root, text="Пауза", command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=3, column=1, padx=10, pady=10, sticky="we")

        self.stop_btn = tk.Button(root, text="Стоп", command=self.stop_download, state="disabled")
        self.stop_btn.grid(row=3, column=2, padx=10, pady=10, sticky="we")

        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="we")

        self.status_label = tk.Label(root, text="Готов к работе", fg="blue")
        self.status_label.grid(row=5, column=0, columnspan=3, padx=10, pady=5)

        root.columnconfigure(1, weight=1)
        self.root.after(100, self.process_queue)

    # ================= МЕНЮ =================
    def _create_menu(self):
        """Создание строки меню."""
        menubar = Menu(self.root)

        # Меню «Файл»
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню «Справка»
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)

        self.root.config(menu=menubar)

    def show_about(self):
        """Показ окна «О программе»."""
        about_win = tk.Toplevel(self.root)
        about_win.title("О программе")
        about_win.geometry("480x400")
        about_win.resizable(False, False)
        about_win.transient(self.root)
        about_win.grab_set()

        # Заголовок
        tk.Label(about_win, text=APP_NAME, font=("Arial", 16, "bold"), fg="#2E7D32").pack(pady=(15, 0))
        tk.Label(about_win, text=f"Версия {APP_VERSION}", font=("Arial", 10), fg="gray").pack()

        # Разделитель
        ttk.Separator(about_win, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # Описание
        tk.Label(about_win, text=APP_DESCRIPTION, justify="left",
                 font=("Arial", 10), wraplength=440).pack(padx=20, anchor="w")

        # Разделитель
        ttk.Separator(about_win, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # Автор
        tk.Label(about_win, text=f"Автор: {APP_AUTHOR}",
                 font=("Arial", 10, "bold")).pack(pady=(0, 2))

        # ---------- Email как кликабельная ссылка ----------
        email_label = tk.Label(
            about_win,
            text=APP_EMAIL,
            font=("Arial", 10, "underline"),
            fg="#0563C1",
            cursor="hand2"
        )
        email_label.pack(pady=(0, 5))

        # Эффект при наведении
        email_label.bind("<Enter>", lambda e: email_label.config(fg="#0A4B8F"))
        email_label.bind("<Leave>", lambda e: email_label.config(fg="#0563C1"))

        # Всплывающая подсказка-статус внизу окна
        hint_label = tk.Label(about_win, text="", font=("Arial", 8), fg="gray")
        hint_label.pack(pady=(0, 2))

        def show_hint(text):
            hint_label.config(text=text)

        def clear_hint(_=None):
            hint_label.config(text="")

        email_label.bind("<Enter>", lambda e: (email_label.config(fg="#0A4B8F"),
                                                show_hint("ЛКМ — открыть почту, ПКМ — меню")), add="+")
        email_label.bind("<Leave>", lambda e: (email_label.config(fg="#0563C1"),
                                                clear_hint()), add="+")

        def open_mail_client(event=None):
            """Попытка открыть почтовый клиент + копирование в буфер."""
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(APP_EMAIL)
                self.root.update()
            except Exception:
                pass

            opened = False
            try:
                opened = webbrowser.open(f"mailto:{APP_EMAIL}")
            except Exception:
                opened = False

            if not opened:
                # Резервный способ для Windows
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(f"mailto:{APP_EMAIL}")
                        opened = True
                except Exception:
                    opened = False

            if opened:
                show_hint("Открываю почтовый клиент…")
            else:
                messagebox.showinfo(
                    "Email скопирован",
                    f"Не удалось открыть почтовый клиент (он не настроен в системе).\n\n"
                    f"Адрес скопирован в буфер обмена:\n{APP_EMAIL}"
                )

        def copy_email(event=None):
            """Копирование email в буфер обмена."""
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(APP_EMAIL)
                self.root.update()
                show_hint("Email скопирован в буфер обмена")
                about_win.after(2000, clear_hint)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось скопировать: {e}")

        # Левая кнопка мыши — открыть почтовый клиент
        email_label.bind("<Button-1>", open_mail_client)

        # Правая кнопка — контекстное меню
        email_menu = Menu(about_win, tearoff=0)
        email_menu.add_command(label="Копировать email", command=copy_email)
        email_menu.add_command(label="Открыть почтовый клиент", command=open_mail_client)

        def show_email_menu(event):
            try:
                email_menu.tk_popup(event.x_root, event.y_root)
            finally:
                email_menu.grab_release()

        email_label.bind("<Button-3>", show_email_menu)
        # ---------------------------------------------------

        # Кнопка «Закрыть»
        tk.Button(about_win, text="Закрыть", width=12, command=about_win.destroy).pack(pady=15)

        # Центрирование окна относительно главного
        about_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - about_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - about_win.winfo_height()) // 2
        about_win.geometry(f"+{x}+{y}")
    # ================= КОНТЕКСТНОЕ МЕНЮ =================
    def _create_context_menu(self):
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Вставить", command=self.paste_url)
        self.context_menu.add_command(label="Вырезать", command=lambda: self.url_entry.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="Копировать", command=lambda: self.url_entry.event_generate("<<Copy>>"))
        self.url_entry.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # ================= ОСНОВНАЯ ЛОГИКА =================
    def paste_url(self):
        try:
            clipboard_text = self.root.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard_text.strip())
            self.status_label.config(text="Ссылка вставлена из буфера обмена", fg="green")
        except tk.TclError:
            messagebox.showerror("Ошибка", "Не удалось прочитать буфер обмена.")

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.folder_path = folder
            self.folder_label.config(text=folder, fg="black")
            self.status_label.config(text=f"Папка выбрана: {folder}", fg="green")
        else:
            if not hasattr(self, 'folder_path'):
                self.folder_label.config(text="Папка не выбрана", fg="gray")

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Предупреждение", "Введите ссылку на видео.")
            return
        if not hasattr(self, 'folder_path'):
            messagebox.showwarning("Предупреждение", "Выберите папку для сохранения.")
            return
        if self.downloading:
            messagebox.showinfo("Информация", "Скачивание уже выполняется.")
            return

        url = url.replace("vkvideo.ru", "vk.com")

        self.progress['value'] = 0
        self.downloading = True
        self.paused = False
        self.stop_requested = False
        self.pause_event.set()
        self.download_btn.config(state='disabled', text="Скачивание...")
        self.pause_btn.config(state='normal', text="Пауза")
        self.stop_btn.config(state='normal')
        self.status_label.config(text="Начинаю скачивание...", fg="blue")

        thread = threading.Thread(target=self.download_video, args=(url, self.folder_path), daemon=True)
        thread.start()

    def download_video(self, url, folder):
        quality = self.quality_var.get()
        format_map = {
            "Лучшее": "best",
            "1080p": "best[height<=1080]",
            "720p": "best[height<=720]",
            "480p": "best[height<=480]",
            "360p": "best[height<=360]",
        }
        format_str = format_map.get(quality, "best")

        user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36")
        ydl_opts = {
            'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
            'format': format_str,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            },
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if not self.stop_requested:
                self.queue.put(('success', "Видео успешно скачано!"))
            else:
                self.queue.put(('status', "Скачивание остановлено пользователем."))
        except Exception as e:
            if self.stop_requested:
                self.queue.put(('status', "Скачивание остановлено."))
            else:
                self.queue.put(('error', f"Ошибка скачивания: {str(e)}"))
        finally:
            self.queue.put(('done', None))

    def progress_hook(self, d):
        if self.stop_requested:
            raise Exception("Остановлено пользователем")
        if self.paused:
            self.pause_event.wait()

        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = downloaded / total * 100
                self.queue.put(('progress', percent))
        elif d['status'] == 'finished':
            self.queue.put(('status', "Обработка видео..."))

    def toggle_pause(self):
        if not self.downloading:
            return
        if self.paused:
            self.paused = False
            self.pause_event.set()
            self.pause_btn.config(text="Пауза")
            self.status_label.config(text="Скачивание продолжено", fg="blue")
        else:
            self.paused = True
            self.pause_event.clear()
            self.pause_btn.config(text="Продолжить")
            self.status_label.config(text="Пауза...", fg="orange")

    def stop_download(self):
        if not self.downloading:
            return
        self.stop_requested = True
        self.pause_event.set()
        self.status_label.config(text="Останавливаю...", fg="red")
        self.stop_btn.config(state='disabled')
        self.pause_btn.config(state='disabled')

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == 'progress':
                    self.progress['value'] = data
                    self.status_label.config(text=f"Скачивание: {data:.1f}%", fg="blue")
                elif msg_type == 'status':
                    self.status_label.config(text=data, fg="blue")
                elif msg_type == 'success':
                    self.progress['value'] = 100
                    self.status_label.config(text=data, fg="green")
                    messagebox.showinfo("Готово", data)
                elif msg_type == 'error':
                    self.status_label.config(text=data, fg="red")
                    messagebox.showerror("Ошибка", data)
                elif msg_type == 'done':
                    self.downloading = False
                    self.paused = False
                    self.stop_requested = False
                    self.pause_event.set()
                    self.download_btn.config(state='normal', text="Скачать")
                    self.pause_btn.config(state='disabled', text="Пауза")
                    self.stop_btn.config(state='disabled')
                    if not self.status_label.cget("text").startswith("Ошибка"):
                        self.status_label.config(text="Готов к работе", fg="blue")
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = AMVideoDownloader(root)
try:
    import pyi_splash
    pyi_splash.close()
except ImportError:
    pass
root.mainloop()