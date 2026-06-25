import os
import sys
import time
import datetime
import subprocess
import threading
import math
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import pystray
from pystray import MenuItem as item

# Thư mục chứa tài nguyên
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Hàm chuyển đổi ảnh trắng thành trong suốt
def make_transparent(image_path):
    try:
        img = Image.open(image_path).convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            r, g, b, a = item
            if r > 240 and g > 240 and b > 240:
                newData.append((255, 255, 255, 0))
            else:
                newData.append((r, g, b, a))
        img.putdata(newData)
        return img
    except Exception:
        return Image.new("RGBA", (200, 200), (0, 0, 0, 0))

# Hàm làm mờ/hòa trộn hình nền
def blend_with_color(image_pil, color_hex, alpha=0.25):
    try:
        image_pil = image_pil.convert("RGBA")
        hex_color = color_hex.lstrip('#')
        rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        solid = Image.new("RGBA", image_pil.size, rgb_color + (255,))
        return Image.blend(solid, image_pil, alpha)
    except Exception:
        return image_pil

# Hàm tạo tấm nền (Card) bo góc
def create_rounded_card(width, height, radius, color_rgba):
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=color_rgba)
    return card

# Hàm lấy tỷ lệ DPI thực tế trên Windows bằng ctypes
def get_dpi_scale():
    if sys.platform == "win32":
        try:
            import ctypes
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88) # LOGPIXELSX = 88
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return dpi / 96.0
        except Exception:
            return 1.0
    return 1.0

class SleepyCatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mèo Cam Ngủ Ngon")
        self.geometry("450x640")
        self.resizable(False, False)
        
        self.scale_factor = get_dpi_scale()
        
        self.current_theme = "light"
        self.transition_active = False

        # Trạng thái hẹn giờ
        self.shutdown_time = None
        self.is_timer_active = False
        self.warning_shown = False
        self.tray_icon = None

        # Tải hình ảnh mèo và hình nền
        self.load_images()

        # Khởi tạo giao diện bằng Canvas
        self.create_widgets()

        # Áp dụng theme mặc định ban đầu
        self.apply_theme("light")

        # Thiết lập icon ứng dụng
        self.after(200, self.set_window_icon)

        # Đăng ký sự kiện tắt ứng dụng
        self.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Bắt đầu luồng kiểm tra thời gian
        self.timer_thread = threading.Thread(target=self.update_timer_loop, daemon=True)
        self.timer_thread.start()

        # Khởi chạy System Tray
        self.tray_thread = threading.Thread(target=self.setup_tray, daemon=True)
        self.tray_thread.start()

        # Tối ưu hóa bộ nhớ RAM sau khi khởi động
        self.after(1000, self.optimize_memory)

    def optimize_memory(self):
        import gc
        gc.collect()
        if sys.platform == "win32":
            try:
                import ctypes
                handle = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
            except Exception:
                pass

    def load_images(self):
        sf = self.scale_factor
        welcome_path = resource_path(os.path.join("assets", "cat_welcome.png"))
        sleep_path = resource_path(os.path.join("assets", "cat_sleep.png"))
        bg_light_path = resource_path(os.path.join("assets", "bg_light.png"))
        bg_dark_path = resource_path(os.path.join("assets", "bg_dark.png"))

        # Transition assets
        circle_path = resource_path(os.path.join("assets", "cat_circle.png"))
        tiny_sleep_path = resource_path(os.path.join("assets", "cat_tiny_sleep.png"))

        # Xử lý ảnh mèo trong suốt
        self.img_welcome_pil = make_transparent(welcome_path).resize((int(200 * sf), int(200 * sf)))
        self.img_sleep_pil = make_transparent(sleep_path).resize((int(200 * sf), int(200 * sf)))
        
        # Load các ảnh động nhỏ cho màn hình chờ chuyển cảnh
        self.img_circle_raw = make_transparent(circle_path).resize((int(100 * sf), int(100 * sf)))
        self.img_tiny_sleep_raw = make_transparent(tiny_sleep_path).resize((int(100 * sf), int(100 * sf)))

        # Tải nền gốc
        try:
            bg_light_raw = Image.open(bg_light_path).resize((int(450 * sf), int(640 * sf)))
            bg_dark_raw = Image.open(bg_dark_path).resize((int(450 * sf), int(640 * sf)))
        except Exception:
            bg_light_raw = Image.new("RGB", (int(450 * sf), int(640 * sf)), "#FDF6F0")
            bg_dark_raw = Image.new("RGB", (int(450 * sf), int(640 * sf)), "#1E1E2F")

        # Làm mờ hình nền để tạo độ tương phản cực tốt
        self.img_bg_light_pil = blend_with_color(bg_light_raw, "#FDF6F0", alpha=0.12)
        self.img_bg_dark_pil = blend_with_color(bg_dark_raw, "#1E1E2F", alpha=0.45)

        # Tạo tấm nền (card) bo góc bán trong suốt
        self.img_card_light_pil = create_rounded_card(int(410 * sf), int(365 * sf), radius=int(25 * sf), color_rgba=(253, 246, 240, 235))
        self.img_card_dark_pil = create_rounded_card(int(410 * sf), int(365 * sf), radius=int(25 * sf), color_rgba=(25, 25, 38, 220))

        import gc
        gc.collect()

    def set_window_icon(self):
        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def create_widgets(self):
        sf = self.scale_factor
        # 1. Tạo Canvas chính
        self.canvas = tk.Canvas(self, width=int(450 * sf), height=int(640 * sf), highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 2. Vẽ hình nền ban đầu lên Canvas
        self.current_bg_tk = ImageTk.PhotoImage(self.img_bg_light_pil)
        self.bg_canvas_id = self.canvas.create_image(0, 0, anchor="nw", image=self.current_bg_tk)

        # 3. Vẽ tấm nền (Card) bo góc đè lên nền
        self.current_card_tk = ImageTk.PhotoImage(self.img_card_light_pil)
        self.card_canvas_id = self.canvas.create_image(int(225 * sf), int(428 * sf), anchor="center", image=self.current_card_tk)

        # 4. Vẽ hình mèo lên Canvas (Sticker)
        self.current_cat_tk = ImageTk.PhotoImage(self.img_welcome_pil)
        self.cat_canvas_id = self.canvas.create_image(int(225 * sf), int(130 * sf), anchor="center", image=self.current_cat_tk)

        # 5. Vẽ tiêu đề lên Canvas (Giới hạn chiều rộng 360px để tự động xuống dòng)
        self.title_text_id = self.canvas.create_text(
            int(225 * sf), int(275 * sf), 
            text="Công chúa muốn hẹn giờ\ntắt máy lúc mấy giờ?", 
            font=("Segoe UI", int(15 * sf), "bold"), 
            fill="#5C4033",
            justify="center",
            width=int(360 * sf)
        )

        # Đồng hồ hiển thị giờ hiện tại ở góc trên bên trái
        self.clock_text_id = self.canvas.create_text(
            int(20 * sf), int(30 * sf),
            text="",
            font=("Segoe UI", int(12 * sf), "bold"),
            fill="#5C4033",
            anchor="w"
        )

        # 6. Vẽ nhãn chủ đề và Toggle Switch
        self.theme_label_id = self.canvas.create_text(
            int(320 * sf), int(30 * sf),
            text="Chế độ tối",
            font=("Segoe UI", int(12 * sf), "bold"),
            fill="#5C4033",
            anchor="e"
        )

        self.theme_switch_var = ctk.StringVar(value="off")
        self.theme_switch = ctk.CTkSwitch(
            self,
            text="",
            command=self.toggle_theme,
            variable=self.theme_switch_var,
            onvalue="on",
            offvalue="off",
            width=45,
            height=20,
            switch_width=40,
            switch_height=18,
            border_width=2,
            border_color="#000000",
            progress_color="#E29578",
            button_color="#6C4E3D",
            button_hover_color="#E29578",
            fg_color="#FFFFFF"
        )
        self.canvas.create_window(int(385 * sf), int(30 * sf), window=self.theme_switch, anchor="center")

        # 7. Khu vực lựa chọn giờ và phút (Dùng CTkComboBox để cuộn chuột và gõ phím được)
        hours = [f"{i:02d}" for i in range(24)]
        self.hour_var = ctk.StringVar(value=datetime.datetime.now().strftime("%H"))
        self.hour_menu = ctk.CTkComboBox(
            self, 
            values=hours, 
            variable=self.hour_var,
            width=75,
            height=34,
            font=("Segoe UI", 14, "bold"),
            dropdown_font=("Segoe UI", 14, "bold"),
            corner_radius=10
        )
        self.canvas.create_window(int(175 * sf), int(330 * sf), window=self.hour_menu, anchor="center")

        # Dấu hai chấm
        self.lbl_colon_id = self.canvas.create_text(
            int(225 * sf), int(330 * sf), 
            text=":", 
            font=("Segoe UI", int(22 * sf), "bold"),
            fill="#5C4033"
        )

        minutes = [f"{i:02d}" for i in range(60)]
        self.minute_var = ctk.StringVar(value=datetime.datetime.now().strftime("%M"))
        self.minute_menu = ctk.CTkComboBox(
            self, 
            values=minutes, 
            variable=self.minute_var,
            width=75,
            height=34,
            font=("Segoe UI", 14, "bold"),
            dropdown_font=("Segoe UI", 14, "bold"),
            corner_radius=10
        )
        self.canvas.create_window(int(275 * sf), int(330 * sf), window=self.minute_menu, anchor="center")

        # 8. Presets Frame
        presets_frame = ctk.CTkFrame(self, fg_color="transparent")
        preset_btn_style = {
            "width": 80,
            "height": 30,
            "corner_radius": 15,
            "font": ("Segoe UI", 12, "bold")
        }

        self.btn_p30 = ctk.CTkButton(presets_frame, text="+30 phút", command=lambda: self.add_preset_minutes(30), **preset_btn_style)
        self.btn_p30.grid(row=0, column=0, padx=5)

        self.btn_p60 = ctk.CTkButton(presets_frame, text="+1 tiếng", command=lambda: self.add_preset_minutes(60), **preset_btn_style)
        self.btn_p60.grid(row=0, column=1, padx=5)

        self.btn_p120 = ctk.CTkButton(presets_frame, text="+2 tiếng", command=lambda: self.add_preset_minutes(120), **preset_btn_style)
        self.btn_p120.grid(row=0, column=2, padx=5)

        self.canvas.create_window(int(225 * sf), int(385 * sf), window=presets_frame, anchor="center")

        # 9. Các nút hành động chính
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_start = ctk.CTkButton(
            actions_frame, 
            text="🐱 Hẹn Giờ Ngay", 
            command=self.start_shutdown_timer,
            width=140,
            height=40,
            font=("Segoe UI", 13, "bold"),
            corner_radius=20
        )
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_cancel = ctk.CTkButton(
            actions_frame, 
            text="Hủy Hẹn Giờ", 
            command=self.cancel_shutdown_timer,
            width=110,
            height=40,
            fg_color="#FF7F7F",
            hover_color="#E56E6E",
            text_color="#FFFFFF",
            font=("Segoe UI", 13, "bold"),
            corner_radius=20
        )
        self.btn_cancel.grid(row=0, column=1, padx=10)

        self.canvas.create_window(int(225 * sf), int(455 * sf), window=actions_frame, anchor="center")

        # 10. Trạng thái và Đếm ngược vẽ trực tiếp lên Canvas
        self.status_text_id = self.canvas.create_text(
            int(225 * sf), int(520 * sf),
            text="Trạng thái: Chưa có hẹn giờ.",
            font=("Segoe UI", int(12 * sf), "italic"),
            fill="#5C4033"
        )

        self.countdown_text_id = self.canvas.create_text(
            int(225 * sf), int(560 * sf),
            text="",
            font=("Segoe UI", int(16 * sf), "bold"),
            fill="#FF4500"
        )

    def apply_theme(self, mode):
        self.current_theme = mode
        if mode == "light":
            ctk.set_appearance_mode("Light")
            self.configure(fg_color="#FDF6F0")
            
            self.current_bg_tk = ImageTk.PhotoImage(self.img_bg_light_pil)
            self.current_card_tk = ImageTk.PhotoImage(self.img_card_light_pil)
            self.current_cat_tk = ImageTk.PhotoImage(self.img_welcome_pil)
            
            self.canvas.itemconfig(self.bg_canvas_id, image=self.current_bg_tk)
            self.canvas.itemconfig(self.card_canvas_id, image=self.current_card_tk)
            self.canvas.itemconfig(self.cat_canvas_id, image=self.current_cat_tk)

            # Cập nhật màu văn bản vẽ trên Canvas
            self.canvas.itemconfig(self.title_text_id, fill="#6C4E3D")
            self.canvas.itemconfig(self.theme_label_id, fill="#6C4E3D", text="Chế độ tối")
            self.canvas.itemconfig(self.clock_text_id, fill="#6C4E3D")
            self.canvas.itemconfig(self.lbl_colon_id, fill="#6C4E3D")
            self.canvas.itemconfig(self.status_text_id, fill="#6C4E3D")
            
            # Cập nhật Switch và Button CTk
            self.theme_switch_var.set("off")
            self.theme_switch.configure(
                border_color="#000000",
                fg_color="#FFFFFF",
                progress_color="#E29578",
                button_color="#6C4E3D",
                button_hover_color="#E29578"
            )
            self.btn_start.configure(fg_color="#E29578", text_color="#FFFFFF", hover_color="#D68466")
            
            # OptionMenu/ComboBox styling
            combobox_style = {
                "fg_color": "#E29578",
                "button_color": "#E29578",
                "button_hover_color": "#D68466",
                "text_color": "#FFFFFF",
                "border_color": "#E29578",
                "dropdown_fg_color": "#FDF6F0",
                "dropdown_text_color": "#6C4E3D",
                "dropdown_hover_color": "#F5CAC3"
            }
            self.hour_menu.configure(**combobox_style)
            self.minute_menu.configure(**combobox_style)
            
            for btn in [self.btn_p30, self.btn_p60, self.btn_p120]:
                btn.configure(fg_color="#F5CAC3", text_color="#6C4E3D", hover_color="#E8B4AC")
        else:
            ctk.set_appearance_mode("Dark")
            self.configure(fg_color="#1E1E2F")
            
            self.current_bg_tk = ImageTk.PhotoImage(self.img_bg_dark_pil)
            self.current_card_tk = ImageTk.PhotoImage(self.img_card_dark_pil)
            self.current_cat_tk = ImageTk.PhotoImage(self.img_sleep_pil)
            
            self.canvas.itemconfig(self.bg_canvas_id, image=self.current_bg_tk)
            self.canvas.itemconfig(self.card_canvas_id, image=self.current_card_tk)
            self.canvas.itemconfig(self.cat_canvas_id, image=self.current_cat_tk)

            # Cập nhật màu văn bản vẽ trên Canvas
            self.canvas.itemconfig(self.title_text_id, fill="#FFE5B4")
            self.canvas.itemconfig(self.theme_label_id, fill="#FFE5B4", text="Chế độ sáng")
            self.canvas.itemconfig(self.clock_text_id, fill="#FFE5B4")
            self.canvas.itemconfig(self.lbl_colon_id, fill="#FFE5B4")
            self.canvas.itemconfig(self.status_text_id, fill="#FFE5B4")
            
            # Cập nhật Switch và Button CTk
            self.theme_switch_var.set("on")
            self.theme_switch.configure(
                border_color="#FFE5B4",
                fg_color="#2D2D44",
                progress_color="#FFB347",
                button_color="#FFE5B4",
                button_hover_color="#FFD39B"
            )
            self.btn_start.configure(fg_color="#E69528", text_color="#1E1E2F", hover_color="#FFB347")
            
            combobox_style = {
                "fg_color": "#2D2D44",
                "button_color": "#2D2D44",
                "button_hover_color": "#3A3A54",
                "text_color": "#FFE5B4",
                "border_color": "#2D2D44",
                "dropdown_fg_color": "#2D2D44",
                "dropdown_text_color": "#FFE5B4",
                "dropdown_hover_color": "#3A3A54"
            }
            self.hour_menu.configure(**combobox_style)
            self.minute_menu.configure(**combobox_style)
            
            for btn in [self.btn_p30, self.btn_p60, self.btn_p120]:
                btn.configure(fg_color="#2A2A3D", text_color="#FFE5B4", hover_color="#3A3A54")

    # Màn hình chờ chuyển cảnh (Onboarding Transition Overlay Screen)
    def start_transition_screen(self, target_mode):
        if self.transition_active:
            return
        self.transition_active = True

        bg_color = "#FDF6F0" if target_mode == "dark" else "#1E1E2F"
        is_spinning = (target_mode == "dark")
        sf = self.scale_factor

        # Sử dụng Canvas thay vì Frame để vẽ trăng sao
        self.overlay_canvas = tk.Canvas(self, width=int(450 * sf), height=int(640 * sf), bg=bg_color, highlightthickness=0)
        self.overlay_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Vẽ trang trí trăng sao cho màn hình chờ màu tối
        if not is_spinning:
            # 1. Vẽ các ngôi sao nhỏ lung linh (vòng tròn vàng nhạt)
            stars = [(60, 80), (120, 150), (80, 250), (350, 120), (380, 280), (100, 480), (360, 500)]
            for sx, sy in stars:
                self.overlay_canvas.create_oval(sx*sf, sy*sf, (sx+4)*sf, (sy+4)*sf, fill="#FFE5B4", outline="")
            
            # 2. Vẽ mặt trăng khuyết màu vàng cam dễ thương ở góc phải
            self.overlay_canvas.create_oval(300*sf, 80*sf, 350*sf, 130*sf, fill="#FFE5B4", outline="")
            self.overlay_canvas.create_oval(315*sf, 80*sf, 365*sf, 130*sf, fill=bg_color, outline="")

        # Nhãn ảnh động ở tâm Canvas
        self.anim_image_id = self.overlay_canvas.create_image(int(225 * sf), int(320 * sf), anchor="center")

        start_time = time.time()
        duration = 0.5

        def animate():
            angle = 0
            while time.time() - start_time < duration:
                if not self.winfo_exists():
                    return
                
                if is_spinning:
                    angle = (angle + 12) % 360
                    rotated = self.img_circle_raw.rotate(-angle)
                    photo = ImageTk.PhotoImage(rotated)
                else:
                    t = time.time() - start_time
                    angle_wiggle = 8 * math.sin(t * 8)
                    wiggled = self.img_tiny_sleep_raw.rotate(angle_wiggle)
                    photo = ImageTk.PhotoImage(wiggled)

                if self.winfo_exists():
                    self.after(0, lambda p=photo: self.update_anim_canvas(p))
                
                time.sleep(0.04)

            self.after(0, lambda: self.finish_transition_screen(target_mode))

        threading.Thread(target=animate, daemon=True).start()

    def update_anim_canvas(self, photo):
        if hasattr(self, "overlay_canvas") and self.overlay_canvas.winfo_exists():
            self.anim_photo_ref = photo
            self.overlay_canvas.itemconfig(self.anim_image_id, image=photo)

    def finish_transition_screen(self, target_mode):
        try:
            # Áp dụng theme
            self.apply_theme(target_mode)
        except Exception as e:
            print(f"Error applying theme: {e}")
        finally:
            # Xóa Canvas chờ
            if hasattr(self, "overlay_canvas") and self.overlay_canvas.winfo_exists():
                self.overlay_canvas.destroy()
            self.transition_active = False

    def toggle_theme(self):
        target = "dark" if self.theme_switch_var.get() == "on" else "light"
        self.start_transition_screen(target)

    # Hàm cộng dồn thời gian khi bấm liên tiếp vào Preset
    def add_preset_minutes(self, minutes):
        try:
            h = int(self.hour_var.get())
            m = int(self.minute_var.get())
        except ValueError:
            now = datetime.datetime.now()
            h, m = now.hour, now.minute

        now = datetime.datetime.now()
        base_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        target = base_time + datetime.timedelta(minutes=minutes)
        
        self.hour_var.set(f"{target.hour:02d}")
        self.minute_var.set(f"{target.minute:02d}")

    def start_shutdown_timer(self):
        try:
            h = int(self.hour_var.get())
            m = int(self.minute_var.get())
            if not (0 <= h <= 23) or not (0 <= m <= 59):
                raise ValueError
        except ValueError:
            now = datetime.datetime.now()
            self.hour_var.set(now.strftime("%H"))
            self.minute_var.set(now.strftime("%M"))
            return

        now = datetime.datetime.now()
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)

        if target <= now:
            target += datetime.timedelta(days=1)

        self.shutdown_time = target
        self.is_timer_active = True
        self.warning_shown = False

        # Bật màn hình chuyển cảnh mượt mà sang Dark Mode
        self.start_transition_screen("dark")
        self.canvas.itemconfig(self.title_text_id, text="Mèo cam đang ngủ ngon giấc... 💤")

        delta_sec = int((target - now).total_seconds())
        
        subprocess.run("shutdown /a", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(f"shutdown /s /f /t {delta_sec}", shell=True)

        self.canvas.itemconfig(self.status_text_id, text=f"Đã hẹn tắt máy lúc: {target.strftime('%H:%M - %d/%m/%Y')}")
        self.show_notification("Hẹn giờ thành công!", f"Máy tính sẽ tắt vào lúc {target.strftime('%H:%M')}. Chúc dien ngủ ngon! 🐾")

    def cancel_shutdown_timer(self):
        self.is_timer_active = False
        self.shutdown_time = None
        self.warning_shown = False

        subprocess.run("shutdown /a", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Bật màn hình chuyển cảnh mượt mà về Light Mode
        self.start_transition_screen("light")
        self.canvas.itemconfig(self.title_text_id, text="Công chúa muốn hẹn giờ\ntắt máy lúc mấy giờ?")
        self.canvas.itemconfig(self.status_text_id, text="Trạng thái: Đã hủy hẹn giờ.")
        self.canvas.itemconfig(self.countdown_text_id, text="")
        
        self.show_notification("Đã hủy hẹn giờ", "Mèo cam đã thức dậy rồi nè! 🐱")

    def update_timer_loop(self):
        while True:
            now = datetime.datetime.now()
            now_str = now.strftime("%H:%M:%S")
            
            # Cập nhật đồng hồ hệ thống góc trên bên trái
            try:
                if self.winfo_exists():
                    self.canvas.itemconfig(self.clock_text_id, text=now_str)
            except Exception:
                pass

            if self.is_timer_active and self.shutdown_time:
                remaining = self.shutdown_time - now
                total_seconds = int(remaining.total_seconds())

                if total_seconds <= 0:
                    self.is_timer_active = False
                    self.shutdown_time = None
                    self.canvas.itemconfig(self.countdown_text_id, text="Đang tắt máy...")
                else:
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    self.canvas.itemconfig(
                        self.countdown_text_id, 
                        text=f"Còn lại: {hours:02d} giờ {minutes:02d} phút {seconds:02d} giây"
                    )

                    if total_seconds <= 300 and not self.warning_shown:
                        self.warning_shown = True
                        self.trigger_warning_popup(total_seconds)

            time.sleep(1)

    def trigger_warning_popup(self, remaining_seconds):
        self.after(0, lambda: self.show_cute_warning(remaining_seconds))

    def show_cute_warning(self, remaining_seconds):
        self.deiconify()
        self.focus_force()

        warning_win = ctk.CTkToplevel(self)
        warning_win.title("Nhắc nhở từ Mèo Cam 🐾")
        warning_win.geometry("380x200")
        warning_win.resizable(False, False)
        
        if self.current_theme == "light":
            warning_win.configure(fg_color="#FFFDF0")
            lbl_color = "#5C4033"
            btn_fg = "#FFB347"
            btn_text = "#5C4033"
            btn_hover = "#E69528"
        else:
            warning_win.configure(fg_color="#1E1E2F")
            lbl_color = "#FFE5B4"
            btn_fg = "#E69528"
            btn_text = "#1E1E2F"
            btn_hover = "#FFB347"

        warning_win.transient(self)
        warning_win.grab_set()

        x = self.winfo_x() + (self.winfo_width() // 2) - 190
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        warning_win.geometry(f"+{x}+{y}")

        # Tính toán thời gian thực tế còn lại
        minutes, seconds = divmod(remaining_seconds, 60)
        if minutes > 0:
            if seconds > 0:
                time_str = f"{minutes} phút {seconds} giây"
            else:
                time_str = f"{minutes} phút"
        else:
            time_str = f"{seconds} giây"

        lbl = ctk.CTkLabel(
            warning_win,
            text=f"dien ơi! Còn đúng {time_str} nữa là\nmáy tính sẽ tự động đi ngủ đó.\nNhớ lưu lại tài liệu nhé!",
            font=("Segoe UI", 14, "bold"),
            text_color=lbl_color,
            pady=20
        )
        lbl.pack()

        btn = ctk.CTkButton(
            warning_win,
            text="Okeeee",
            command=warning_win.destroy,
            fg_color=btn_fg,
            hover_color=btn_hover,
            text_color=btn_text,
            font=("Segoe UI", 12, "bold"),
            corner_radius=15,
            width=150,
            height=35
        )
        btn.pack(pady=10)

    def setup_tray(self):
        image = self.img_welcome_pil.resize((64, 64))
        
        menu = (
            item('Hiện ứng dụng', self.show_app),
            item('Hủy hẹn giờ', self.tray_cancel),
            item('Thoát hoàn toàn', self.exit_app)
        )
        
        self.tray_icon = pystray.Icon("SleepyCat", image, "Mèo Cam Ngủ Ngon", menu)
        self.tray_icon.run()

    def hide_to_tray(self):
        self.withdraw()
        self.show_notification("Mèo Cam đang chạy ngầm", "App đã được thu nhỏ xuống khay hệ thống ở góc dưới bên phải màn hình nè!")
        self.optimize_memory()

    def show_app(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)

    def tray_cancel(self, icon=None, item=None):
        self.after(0, self.cancel_shutdown_timer)

    def exit_app(self, icon=None, item=None):
        subprocess.run("shutdown /a", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.destroy)
        sys.exit(0)

    def show_notification(self, title, message):
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            threading.Thread(target=toaster.show_toast, args=(title, message, None, 4), daemon=True).start()
        except ImportError:
            pass

if __name__ == "__main__":
    app = SleepyCatApp()
    app.mainloop()
