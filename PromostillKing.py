# Promostill King — App version v1.14 (restore button click handlers)
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import tkinter.font as tkfont
from PIL import Image, ImageTk, ImageEnhance
import os, sys, cv2, traceback, json
from datetime import datetime

APP_VERSION = "v1.14 (restore button click handlers)"
LOG_PATH = os.path.join(os.path.expanduser("~"), "Library", "Logs", "PromostillKing.log")
PREFS_PATH = os.path.join(os.path.expanduser("~"), "Library", "Preferences", "PromostillKing.json")

DEFAULT_PREFS = {
    "vlist_x": 117,
    "vlist_y": 72,
    "vlist_w": 199,
    "vlist_h": 131,
    "bg": "#93e18d",
    "fg": "#125266",
    "font_family": "Arial Rounded MT Bold",
    "font_size": 15
}

def log(msg: str):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass

def load_prefs():
    prefs = DEFAULT_PREFS.copy()
    try:
        if os.path.exists(PREFS_PATH):
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in prefs:
                    prefs[k] = v
    except Exception:
        log("Failed to load prefs; using defaults.")
    return prefs

def save_prefs(prefs: dict):
    try:
        os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
        log(f"Saved prefs to {PREFS_PATH}")
    except Exception:
        log("Failed to save prefs:\n" + traceback.format_exc())

def resource_path(name: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        p = os.path.join(sys._MEIPASS, name)
        if os.path.exists(p): return p
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        for c in (
            os.path.join(exe_dir, name),
            os.path.abspath(os.path.join(exe_dir, "..", "Resources", name)),
            os.path.abspath(os.path.join(exe_dir, "Resources", name)),
        ):
            if os.path.exists(c): return c
        return os.path.join(exe_dir, name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)

def asset(rel_in_images: str) -> str:
    candidates = [os.path.join("images", rel_in_images), rel_in_images]
    for rel in candidates:
        p = resource_path(rel)
        if os.path.exists(p):
            return p
    return resource_path(os.path.join("images", rel_in_images))

def open_snapshot_viewer(video_path, save_dir):
    """
    Snapshot viewer:
      - S to save current frame as Promostill_###.jpg
      - SPACE to skip to next timestamp
      - Q (or q) or ESC or closing the window quits
      - Steps ~30 seconds per frame (based on FPS)
    """
    log(f"Opening viewer for: {video_path} -> {save_dir}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        log("❌ Error opening video.")
        messagebox.showerror("Promostill King", "Error opening video file.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_jump = int(fps * 30)  # 30-second step
    current_frame = 0
    snapshot_count = 1

    win = "Snapshot Viewer  —  SPACE=Skip  S=Save  Q=Quit"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    try:
        while True:
            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                log("Viewer window closed by user.")
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret:
                log("🎞️ End of video.")
                break

            show = frame.copy()
            cv2.putText(show, f"Frame: {current_frame}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow(win, show)

            key = cv2.waitKeyEx(0) & 0xFF
            if key in (ord('q'), ord('Q'), 27):  # ESC
                log("Viewer quit by user (q/Q/ESC).")
                break
            elif key in (ord('s'), ord('S')):
                fname = f"Promostill_{snapshot_count:03d}.jpg"
                out_path = os.path.join(save_dir, fname)
                cv2.imwrite(out_path, frame)
                log(f"✅ Saved {out_path}")
                snapshot_count += 1
                current_frame += frame_jump
            else:
                current_frame += frame_jump
    except Exception:
        log("Error inside viewer loop:\n" + traceback.format_exc())
    finally:
        cap.release()
        try:
            cv2.destroyWindow(win)
        except Exception:
            pass
        cv2.waitKey(1)

class PromostillKingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Promostill King")
        self.geometry("900x600")
        self.resizable(False, False)
        self.video_path = None
        self.output_dir = None
        self.video_history = []
        self.prefs = load_prefs()

        # Background
        bg_file = asset("castle_background.png")
        log(f"{APP_VERSION} — Using background: {bg_file}")
        if not os.path.exists(bg_file):
            log(f"Missing asset: {bg_file}")
            try:
                messagebox.showerror("Promostill King", f"Missing image:\n{bg_file}")
            except Exception:
                pass
            raise FileNotFoundError(f"Missing asset: {bg_file}")
        bg_image = Image.open(bg_file).resize((900, 600))
        self.bg_photo = ImageTk.PhotoImage(bg_image)

        self.canvas = tk.Canvas(self, width=900, height=600, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")

        # Button images + hover
        def load_img(name):
            return Image.open(asset(name))
        def load_pair(name):
            base = load_img(name)
            hover = ImageEnhance.Brightness(base).enhance(0.85)  # darken ~15%
            return ImageTk.PhotoImage(base), ImageTk.PhotoImage(hover)

        browse_norm, browse_hover = load_pair("browse_button_fixed.png")
        clear_norm,  clear_hover  = load_pair("clear_button_fixed.png")
        folder_norm, folder_hover = load_pair("folder_button_fixed.png")
        gen_norm,    gen_hover    = load_pair("generate_button_fixed.png")

        # Positions (unchanged)
        self.browse_id   = self.canvas.create_image(53, 190, image=browse_norm, anchor="nw")
        self.clear_id    = self.canvas.create_image(95, 376, image=clear_norm,  anchor="nw")
        self.generate_id = self.canvas.create_image(471, 376, image=gen_norm,   anchor="nw")
        self.folder_id   = self.canvas.create_image(543, 179, image=folder_norm,anchor="nw")

        # Keep refs
        self._img_refs = {
            "browse_norm": browse_norm, "browse_hover": browse_hover,
            "clear_norm":  clear_norm,  "clear_hover":  clear_hover,
            "folder_norm": folder_norm, "folder_hover": folder_hover,
            "gen_norm":    gen_norm,    "gen_hover":    gen_hover,
        }

        # Hover behavior
        def bind_hover(item_id, norm_key, hover_key):
            self.canvas.tag_bind(item_id, "<Enter>",
                lambda e: self.canvas.itemconfigure(item_id, image=self._img_refs[hover_key]))
            self.canvas.tag_bind(item_id, "<Leave>",
                lambda e: self.canvas.itemconfigure(item_id, image=self._img_refs[norm_key]))
        bind_hover(self.browse_id,   "browse_norm", "browse_hover")
        bind_hover(self.clear_id,    "clear_norm",  "clear_hover")
        bind_hover(self.folder_id,   "folder_norm", "folder_hover")
        bind_hover(self.generate_id, "gen_norm",    "gen_hover")

        # ✅ Click handlers (restored)
        self.canvas.tag_bind(self.browse_id,   "<Button-1>", self.select_video)
        self.canvas.tag_bind(self.clear_id,    "<Button-1>", self.clear_paths)
        self.canvas.tag_bind(self.folder_id,   "<Button-1>", self.select_folder)
        self.canvas.tag_bind(self.generate_id, "<Button-1>", self.generate_snapshots)

        # Selected Videos list (customizable)
        self.v_font = tkfont.Font(family=self.prefs["font_family"], size=self.prefs["font_size"])
        self.vlist_label = tk.Label(self, text="Selected Videos",
                                    bg=self.prefs["bg"], fg=self.prefs["fg"], font=self.v_font)
        self.video_list = tk.Listbox(self, bg=self.prefs["bg"], fg=self.prefs["fg"], font=self.v_font)
        self._apply_prefs_live(initial=True)

        # Customize panel shortcuts
        self.bind_all("<Command-comma>", self.open_customize)
        self.bind_all("<Key-c>", self.open_customize)

        self.after(100, self._force_front)

    def _force_front(self):
        try:
            self.lift()
            self.attributes("-topmost", True)
            self.after(500, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def _add_to_history(self, path: str):
        if not path:
            return
        self.video_history.append(path)
        self.video_list.insert(tk.END, os.path.basename(path))

    def _apply_prefs_live(self, initial=False):
        try:
            self.v_font.config(family=self.prefs["font_family"], size=self.prefs["font_size"])
            x = int(self.prefs["vlist_x"]); y = int(self.prefs["vlist_y"])
            w = max(80, int(self.prefs["vlist_w"])); h = max(80, int(self.prefs["vlist_h"]))
            if initial:
                self.vlist_label.place(x=x, y=y-22, width=w, height=22)
                self.video_list.place(x=x, y=y, width=w, height=h)
            else:
                self.vlist_label.place_configure(x=x, y=y-22, width=w, height=22)
                self.video_list.place_configure(x=x, y=y, width=w, height=h)
            self.video_list.config(bg=self.prefs["bg"], fg=self.prefs["fg"])
            self.vlist_label.config(bg=self.prefs["bg"], fg=self.prefs["fg"])
        except Exception:
            log("Failed to apply prefs live:\n" + traceback.format_exc())

    def open_customize(self, event=None):
        try:
            dlg = tk.Toplevel(self)
            dlg.title("Customize Selected Videos Panel")
            dlg.geometry("460x340")
            dlg.resizable(False, False)
            dlg.transient(self)
            dlg.grab_set()

            fam_var  = tk.StringVar(value=self.prefs["font_family"])
            size_var = tk.IntVar(value=self.prefs["font_size"])
            x_var    = tk.IntVar(value=self.prefs["vlist_x"])
            y_var    = tk.IntVar(value=self.prefs["vlist_y"])
            w_var    = tk.IntVar(value=self.prefs["vlist_w"])
            h_var    = tk.IntVar(value=self.prefs["vlist_h"])
            bg_var   = tk.StringVar(value=self.prefs["bg"])
            fg_var   = tk.StringVar(value=self.prefs["fg"])

            def pick_bg():
                c = colorchooser.askcolor(color=bg_var.get(), title="Pick Background Color")
                if c and c[1]:
                    bg_var.set(c[1]); self.prefs["bg"] = c[1]; self._apply_prefs_live()

            def pick_fg():
                c = colorchooser.askcolor(color=fg_var.get(), title="Pick Text Color")
                if c and c[1]:
                    fg_var.set(c[1]); self.prefs["fg"] = c[1]; self._apply_prefs_live()

            def on_family(*_):
                self.prefs["font_family"] = fam_var.get(); self._apply_prefs_live()

            def on_size(*_):
                try:
                    self.prefs["font_size"] = int(size_var.get()); self._apply_prefs_live()
                except Exception:
                    pass

            def on_pos(*_):
                try:
                    self.prefs["vlist_x"] = int(x_var.get())
                    self.prefs["vlist_y"] = int(y_var.get())
                    self._apply_prefs_live()
                except Exception:
                    pass

            def on_size_wh(*_):
                try:
                    self.prefs["vlist_w"] = int(w_var.get())
                    self.prefs["vlist_h"] = int(h_var.get())
                    self._apply_prefs_live()
                except Exception:
                    pass

            def reset_defaults():
                for k, v in DEFAULT_PREFS.items():
                    self.prefs[k] = v
                fam_var.set(self.prefs["font_family"])
                size_var.set(self.prefs["font_size"])
                x_var.set(self.prefs["vlist_x"])
                y_var.set(self.prefs["vlist_y"])
                w_var.set(self.prefs["vlist_w"])
                h_var.set(self.prefs["vlist_h"])
                bg_var.set(self.prefs["bg"])
                fg_var.set(self.prefs["fg"])
                self._apply_prefs_live()

            def save_and_close():
                save_prefs(self.prefs)
                dlg.destroy()

            row = 10
            tk.Label(dlg, text="Font Family").place(x=20, y=row)
            fams = sorted(set(tkfont.families()))
            tk.OptionMenu(dlg, fam_var, *fams, command=lambda *_: on_family())\
                .place(x=140, y=row-4, width=280, height=26)

            row += 36
            tk.Label(dlg, text="Font Size").place(x=20, y=row)
            tk.Spinbox(dlg, from_=8, to=48, textvariable=size_var, width=6,
                       command=on_size).place(x=140, y=row-2, width=70)
            size_var.trace_add("write", lambda *_: on_size())

            row += 36
            tk.Label(dlg, text="List X").place(x=20, y=row)
            tk.Spinbox(dlg, from_=0, to=900, textvariable=x_var, width=8,
                       command=on_pos).place(x=140, y=row-2, width=80)
            tk.Label(dlg, text="List Y").place(x=240, y=row)
            tk.Spinbox(dlg, from_=0, to=600, textvariable=y_var, width=8,
                       command=on_pos).place(x=290, y=row-2, width=80)
            x_var.trace_add("write", lambda *_: on_pos())
            y_var.trace_add("write", lambda *_: on_pos())

            row += 36
            tk.Label(dlg, text="List Width").place(x=20, y=row)
            tk.Spinbox(dlg, from_=80, to=500, textvariable=w_var, width=8,
                       command=on_size_wh).place(x=140, y=row-2, width=80)
            tk.Label(dlg, text="List Height").place(x=240, y=row)
            tk.Spinbox(dlg, from_=80, to=500, textvariable=h_var, width=8,
                       command=on_size_wh).place(x=320, y=row-2, width=80)
            w_var.trace_add("write", lambda *_: on_size_wh())
            h_var.trace_add("write", lambda *_: on_size_wh())

            row += 36
            tk.Label(dlg, text="Background").place(x=20, y=row)
            tk.Entry(dlg, textvariable=bg_var).place(x=140, y=row-2, width=120)
            tk.Button(dlg, text="Pick…", command=pick_bg).place(x=270, y=row-4, width=60)

            row += 36
            tk.Label(dlg, text="Text Color").place(x=20, y=row)
            tk.Entry(dlg, textvariable=fg_var).place(x=140, y=row-2, width=120)
            tk.Button(dlg, text="Pick…", command=pick_fg).place(x=270, y=row-4, width=60)

            row += 46
            tk.Button(dlg, text="Reset to Defaults", command=reset_defaults)\
                .place(x=20, y=row, width=150, height=28)
            tk.Button(dlg, text="Save & Close", command=save_and_close)\
                .place(x=260, y=row, width=150, height=28)

            self._apply_prefs_live()
        except Exception:
            log("Customize dialog error:\n" + traceback.format_exc())

    # Actions
    def select_video(self, event=None):
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video files", "*.mp4 *.mov *.m4v *.avi *.mkv")]
        )
        if path:
            self.video_path = path
            self._add_to_history(path)
        log(f"Video selected: {self.video_path}")

    def select_folder(self, event=None):
        self.output_dir = filedialog.askdirectory(title="Select Output Folder")
        log(f"Output folder: {self.output_dir}")

    def clear_paths(self, event=None):
        self.video_path = None
        self.output_dir = None
        self.video_history.clear()
        try:
            self.video_list.delete(0, tk.END)
        except Exception:
            pass
        log("Cleared video(s) and folder selection.")

    def generate_snapshots(self, event=None):
        if self.video_path and (not self.video_history or self.video_history[-1] != self.video_path):
            self._add_to_history(self.video_path)

        if not self.video_path or not self.output_dir:
            messagebox.showwarning("Promostill King", "Please select a video and an output folder first.")
            log("Generate clicked without video/folder.")
            return
        open_snapshot_viewer(self.video_path, self.output_dir)

if __name__ == "__main__":
    try:
        log("App starting… " + APP_VERSION)
        app = PromostillKingApp()
        app.mainloop()
        log("App closed normally.")
    except Exception as e:
        log("\n=== Crash ===\n" + traceback.format_exc())
        try:
            r = tk.Tk(); r.withdraw()
            messagebox.showerror("Promostill King crashed", str(e))
        except Exception:
            pass
