import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import winsound
import threading
import serial
import serial.tools.list_ports
import time
import cv2
from pyzbar.pyzbar import decode
from PIL import Image, ImageTk

class QRCodeValidatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QR Code Validator")
        self.root.geometry("900x900") # Increased size significantly for 640x480 video
        
        # State variables
        self.target_code = tk.StringVar()
        self.scanned_code = tk.StringVar()
        self.selected_source = tk.StringVar(value="Standard Mode (Keyboard)")
        self.is_monitoring = True
        
        # Connections
        self.serial_connection = None
        self.camera_cap = None
        self.stop_event = threading.Event()
        self.camera_index = 0  # Default camera index
        
        # Locking State
        self.is_locked = False
        self.PIN_CODE = "2025"

        # Styles
        self.default_bg = "#f0f0f0"
        self.success_bg = "#90EE90"  # Light Green
        self.error_bg = "#FF6347"    # Tomato Red
        self.root.configure(bg=self.default_bg)

        self._build_ui()
        
        # Bind enter key for the scanner input (Standard Mode)
        self.root.bind('<Return>', self.on_scan_keyboard)
        
        # Start looking for focus or serial
        self.check_mode_loop()
        
        # Cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        # --- Top Section: Settings ---
        self.frame_top = tk.Frame(self.root, bg=self.default_bg, pady=10)
        self.frame_top.pack(fill=tk.X)

        self.lbl_target = tk.Label(self.frame_top, text="1. TARGET CODE (Mã Chuẩn):", bg=self.default_bg, font=("Arial", 11, "bold"))
        self.lbl_target.pack()
        
        self.combo_target = ttk.Combobox(self.frame_top, textvariable=self.target_code, font=("Arial", 12), width=30, justify='center')
        self.combo_target.pack(pady=5)
        
        self.btn_frame = tk.Frame(self.frame_top, bg=self.default_bg)
        self.btn_frame.pack()
        
        self.btn_load = tk.Button(self.btn_frame, text="Load List (txt/csv)", command=self.load_list_file)
        self.btn_load.pack(side=tk.LEFT, padx=5)
        
        self.btn_clear = tk.Button(self.btn_frame, text="Clear", command=self.reset_state)
        self.btn_clear.pack(side=tk.LEFT, padx=5)
        
        # Lock/Unlock Button
        self.btn_lock = tk.Button(self.btn_frame, text="SAVE (LOCK)", command=self.lock_settings, bg="#DDDDDD", font=("Arial", 9, "bold"))
        self.btn_lock.pack(side=tk.LEFT, padx=20)

        ttk.Separator(self.frame_top, orient='horizontal').pack(fill='x', pady=15)

        # 2. Scanner Source Selection
        self.lbl_source = tk.Label(self.frame_top, text="2. SCANNER SOURCE (Nguồn Scan):", bg=self.default_bg, font=("Arial", 11, "bold"))
        self.lbl_source.pack()
        
        self.combo_source = ttk.Combobox(self.frame_top, textvariable=self.selected_source, font=("Arial", 12), width=40, state="readonly")
        self.combo_source.pack(pady=5)
        self.combo_source.bind("<<ComboboxSelected>>", self.on_source_change)
        
        self.btn_refresh = tk.Button(self.frame_top, text="Refresh Ports", command=self.refresh_ports)
        self.btn_refresh.pack(pady=2)

        # --- Middle Section: Status Display & Camera ---
        self.frame_status = tk.Frame(self.root, bg=self.default_bg, pady=10)
        self.frame_status.pack(expand=True, fill=tk.BOTH)

        self.lbl_status = tk.Label(self.frame_status, text="READY", font=("Arial", 16, "bold"), bg=self.default_bg, wraplength=880)
        self.lbl_status.pack(pady=5)
        
        self.lbl_detail = tk.Label(self.frame_status, text="...", font=("Arial", 12), bg=self.default_bg)
        self.lbl_detail.pack(pady=2)
        
        # Camera Preview Label
        self.lbl_video = tk.Label(self.frame_status, bg="black")
        self.lbl_video.pack(pady=10)
        # Hide it initially
        self.lbl_video.pack_forget()

        # --- Bottom Section: Scanner Input (Visible only for Keyboard Mode) ---
        self.frame_bottom = tk.Frame(self.root, bg="#ddd", height=40)
        self.frame_bottom.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.lbl_input = tk.Label(self.frame_bottom, text="Scanner Output:", bg="#ddd")
        self.lbl_input.pack(side=tk.LEFT, padx=5)
        
        self.scanner_entry = tk.Entry(self.frame_bottom, textvariable=self.scanned_code, font=("Arial", 10), width=40)
        self.scanner_entry.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Initial Ports Load
        self.refresh_ports()

    def lock_settings(self):
        if not self.target_code.get():
             if not messagebox.askyesno("Confirm", "Chưa chọn Mã Chuẩn. Bạn có chắc chắn muốn khóa không?"):
                 return
        self.is_locked = True
        self.update_lock_ui()
    
    def unlock_settings(self):
        pin = simpledialog.askstring("Security Check", "Nhập mã PIN để mở khóa:", parent=self.root, show='*')
        if pin == self.PIN_CODE:
            self.is_locked = False
            self.update_lock_ui()
            messagebox.showinfo("Unlocked", "Đã mở khóa cài đặt.")
        elif pin is not None: 
            messagebox.showerror("Wrong PIN", "Mã PIN không đúng!")

    def update_lock_ui(self):
        state = 'disabled' if self.is_locked else 'normal'
        readonly = 'disabled' if self.is_locked else 'readonly'
        self.combo_target.config(state=state)
        self.btn_load.config(state=state)
        self.btn_clear.config(state=state)
        self.combo_source.config(state=readonly)
        self.btn_refresh.config(state=state)
        if self.is_locked:
            self.btn_lock.config(text="CHANGE (UNLOCK)", command=self.unlock_settings, bg="#FFD700") 
        else:
            self.btn_lock.config(text="SAVE (LOCK)", command=self.lock_settings, bg="#DDDDDD")

    def refresh_ports(self):
        if self.is_locked: return
        ports = serial.tools.list_ports.comports()
        
        # Static camera list to avoid probing crashes at startup
        # Listing more cameras to help user find the USB one
        camera_list = [f"Camera {i}" for i in range(5)]
        
        # Build source list: Keyboard, generic Camera Mode, individual cameras, then serial ports
        port_list = ["Standard Mode (Keyboard)"] + camera_list + [f"{p.device} - {p.description}" for p in ports]
        self.combo_source['values'] = port_list
        if self.selected_source.get() not in port_list:
            self.selected_source.set(port_list[0])

    def stop_all_sources(self):
        """Stop serial and camera threads."""
        self.stop_event.set()
        
        # Close Serial
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        
        # Release Camera
        if self.camera_cap and self.camera_cap.isOpened():
            self.camera_cap.release()
        
        self.lbl_video.pack_forget() # Hide video preview

    def on_source_change(self, event):
        if self.is_locked: return
        selection = self.selected_source.get()
        
        self.stop_all_sources()
        time.sleep(0.1)  # Brief pause to allow threads to exit
        
        if "Standard Mode" in selection:
            self.scanner_entry.config(state='normal')
            self.set_status("READY (KEYBOARD)", self.default_bg)
        elif selection.startswith("Camera"):
            # Extract camera index from selection string
            try:
                self.camera_index = int(selection.split()[1])
            except Exception:
                self.camera_index = 0
            self.scanner_entry.delete(0, tk.END)
            self.scanner_entry.config(state='disabled')
            self.start_camera()
        elif "Camera Mode" in selection:
            # Fallback generic camera mode uses default index 0
            self.camera_index = 0
            self.scanner_entry.delete(0, tk.END)
            self.scanner_entry.config(state='disabled')
            self.start_camera()
        else:
            self.scanner_entry.delete(0, tk.END)
            self.scanner_entry.config(state='disabled')
            self.start_serial_listener(selection)

    # --- Camera Logic ---
    def start_camera(self):
        self.stop_event.clear()
        
        # Force show the video label immediately with placeholder
        self.lbl_video.config(width=640, height=480, bg="black", image="", text="Connecting to Camera...", fg="white")
        self.lbl_video.pack(pady=10)
        self.root.update_idletasks()
        
        # Try to open camera
        # Use selected camera index (default 0)
        idx = getattr(self, 'camera_index', 0)
        self.camera_cap = cv2.VideoCapture(idx)
        
        if not self.camera_cap.isOpened():
            self.lbl_video.config(text=f"Cannot open Camera {idx}")
            messagebox.showerror("Error", f"Could not open Webcam {idx}.")
            return

        self.set_status("READY (CAMERA)", self.default_bg)
        threading.Thread(target=self.camera_loop, daemon=True).start()

    def camera_loop(self):
        last_scan_time = 0
        fail_count = 0
        while not self.stop_event.is_set():
            if not self.camera_cap or not self.camera_cap.isOpened():
                time.sleep(1)
                continue
                
            try:
                ret, frame = self.camera_cap.read()
            except Exception as e:
                print(f"Camera Read Error: {e}")
                ret = False
                frame = None

            if ret:
                fail_count = 0
                # Decode QR
                try:
                    decoded_objects = decode(frame)
                except: decoded_objects = []
                
                current_time = time.time()
                
                for obj in decoded_objects:
                    code = obj.data.decode("utf-8")
                    if code and (current_time - last_scan_time > 2.0):
                         last_scan_time = current_time
                         self.root.after(0, lambda c=code: self.process_scan(c))
                    
                    # Draw rect
                    try:
                        rect = obj.rect
                        cv2.rectangle(frame, (rect.left, rect.top), (rect.left + rect.width, rect.top + rect.height), (0, 255, 0), 2)
                    except: pass

                # Convert for Tkinter
                try:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (640, 480)) # Larger video size
                    img = Image.fromarray(frame)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.root.after(0, lambda i=imgtk: self.update_video_label(i))
                except Exception: pass
            else:
                fail_count += 1
                if fail_count > 10:
                     self.root.after(0, lambda: self.lbl_video.config(image="", text="NO SIGNAL / CAMERA ERROR"))
                     # Try to re-open if too many failures
                     if fail_count % 50 == 0:
                         print("Attempting to re-open camera...")
                         try:
                             self.camera_cap.release()
                             self.camera_cap = cv2.VideoCapture(0)
                         except: pass
                time.sleep(0.1)
            
            time.sleep(0.03)

    def update_video_label(self, imgtk):
        if self.stop_event.is_set(): return
        # config text="" to remove any error message if image is showing
        self.lbl_video.configure(image=imgtk, text="", width=640, height=480)
        self.lbl_video.image = imgtk # Keep reference

    # --- Serial Logic ---
    def start_serial_listener(self, port_info):
        port = port_info.split(" - ")[0]
        self.stop_event.clear()
        
        def listen():
            try:
                self.serial_connection = serial.Serial(port, 9600, timeout=1)
                self.root.after(0, lambda: self.set_status(f"CONNECTED: {port}", self.default_bg))
                buffer = ""
                while not self.stop_event.is_set():
                    if self.serial_connection.in_waiting > 0:
                        try:
                            data = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
                            buffer += data
                            if '\r' in buffer or '\n' in buffer:
                                code = buffer.strip()
                                buffer = ""
                                if code:
                                    self.root.after(0, lambda c=code: self.process_scan(c))
                        except Exception: pass
                    time.sleep(0.05)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Serial Error", str(e)))
                self.root.after(0, lambda: self.selected_source.set("Standard Mode (Keyboard)"))

        threading.Thread(target=listen, daemon=True).start()

    def check_mode_loop(self):
        if "Standard Mode" in self.selected_source.get() and not self.is_locked:
            try:
                focus_now = self.root.focus_get()
                if focus_now not in [self.combo_target, self.combo_source, self.btn_load, self.btn_refresh, self.btn_clear]:
                     self.scanner_entry.focus_set()
            except: pass
        if "Standard Mode" in self.selected_source.get() and self.is_locked:
             self.scanner_entry.focus_set()
        self.root.after(1000, self.check_mode_loop)

    def load_list_file(self):
        if self.is_locked: return
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = [line.strip() for line in f.read().splitlines() if line.strip()]
                if content:
                    self.combo_target['values'] = content
                    self.combo_target.current(0)
                    messagebox.showinfo("Success", f"Loaded {len(content)} codes.")
                else: messagebox.showwarning("Warning", "File is empty.")
            except Exception as e: messagebox.showerror("Error", f"Could not read file: {e}")

    def reset_state(self):
        if self.is_locked: return
        self.target_code.set("")
        self.scanned_code.set("")
        self.combo_target['values'] = []
        self.set_status("READY", self.default_bg)

    def on_scan_keyboard(self, event=None):
        if "Standard Mode" not in self.selected_source.get(): return
        if not self.is_locked and self.root.focus_get() in [self.combo_target, self.combo_source]: return
        code = self.scanned_code.get().strip()
        self.scanned_code.set("")
        if code: self.process_scan(code)

    def process_scan(self, scanned_code):
        target = self.target_code.get().strip()
        if not target:
            self.set_status("NO TARGET SELECTED", "#FFFFE0") 
            winsound.Beep(500, 200)
            return
        if scanned_code == target: self.handle_match(scanned_code)
        else: self.handle_mismatch(scanned_code, target)

    def set_status(self, text, bg_color, detail=""):
        self.lbl_status.config(text=text, bg=bg_color)
        self.lbl_detail.config(text=detail, bg=bg_color)
        self.frame_status.config(bg=bg_color)
        self.root.configure(bg=bg_color)

    def handle_match(self, code):
        self.set_status("OK - MATCHED", self.success_bg, f"Code: {code}")
        threading.Thread(target=lambda: winsound.Beep(1000, 200)).start()

    def handle_mismatch(self, scanned, target):
        self.set_status("WRONG !!!", self.error_bg, f"Expected: {target}\nScanned: {scanned}")
        def alert():
            for _ in range(3): winsound.Beep(2000, 300); winsound.Beep(1500, 300)
        threading.Thread(target=alert).start()
        
    def on_close(self):
        self.stop_all_sources()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = QRCodeValidatorApp(root)
    root.mainloop()
