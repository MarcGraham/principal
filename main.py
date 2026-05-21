import tkinter as tk
from tkinter import messagebox
import time, random
from datetime import datetime

# ─── macOS Hardware Simulation ────────────────────────────────────────────────
class MockGPIO:
    def __init__(self, pin, active_high=False, initial_value=False):
        self.pin = pin
        print(f"[MOCK] Simulated relay initialized on Pin {pin}")
    def on(self):
        print("\n" + "="*50)
        print("[HARDWARE] Maglock Released! Exit Door Unlocked.")
        print("="*50 + "\n")

door_lock = MockGPIO(18)

# ─── Config ───────────────────────────────────────────────────────────────────
COMP_PASSWORD    = "admin"
PORTAL_PASSWORD  = "override"
student_grades   = {"Math": "F", "History": "F", "Chemistry": "F"}
escape_timestamps = []

# ─── Color Helpers ────────────────────────────────────────────────────────────
def hex_rgb(h):
    h = h.lstrip('#')
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def lerp_color(c1, c2, t):
    r1,g1,b1 = hex_rgb(c1)
    r2,g2,b2 = hex_rgb(c2)
    return '#{:02x}{:02x}{:02x}'.format(
        int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))

def fill_gradient(canvas, x0, y0, x1, y1, c1, c2, steps=100):
    """Paint a smooth vertical gradient band on a Canvas."""
    h    = y1 - y0
    band = max(1, h // steps)
    for i in range(0, h, band):
        t = i / max(h, 1)
        canvas.create_rectangle(x0, y0+i, x1, y0+i+band,
                                 fill=lerp_color(c1, c2, t), outline='')

def glow_rect(canvas, x0, y0, x1, y1, color):
    """Simulated neon glow halo using stippled concentric rectangles."""
    for spread, stipple in ((24,'gray12'), (15,'gray25'), (8,'gray50')):
        canvas.create_rectangle(x0-spread, y0-spread, x1+spread, y1+spread,
                                 fill=color, stipple=stipple, outline='')

def shadow_text(canvas, x, y, text, **kw):
    """Draw text with a fixed dark drop shadow for depth."""
    shadow_kw = dict(kw)
    shadow_kw['fill'] = '#000000'
    canvas.create_text(x+2, y+2, text=text, **shadow_kw)
    canvas.create_text(x,   y,   text=text, **kw)

# ─── GM Backdoor ─────────────────────────────────────────────────────────────
def gm_backdoor_trigger(event):
    """Hold Control+Option, tap Escape 3× quickly (< 1.5 s) to exit."""
    current_time = time.time()
    escape_timestamps.append(current_time)
    if len(escape_timestamps) > 3:
        escape_timestamps.pop(0)
    if len(escape_timestamps) == 3:
        if escape_timestamps[2] - escape_timestamps[0] < 1.5:
            print("[GM] Backdoor triggered successfully. Exiting program.")
            root.destroy()

# ─── Custom Styled Dialog ─────────────────────────────────────────────────────
class StyledWindow(tk.Toplevel):
    WIN_BG = '#f2ede0'
    BAR_H  = 32

    def __init__(self, parent, title, width, height):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=self.WIN_BG)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f'{width}x{height}+{(sw-width)//2}+{(sh-height)//2}')
        self.configure(highlightbackground='#081a42', highlightthickness=2)

        self._tc = tk.Canvas(self, height=self.BAR_H, highlightthickness=0)
        self._tc.pack(fill=tk.X, side=tk.TOP)
        self._title_text = title
        self._tc.bind('<Configure>', self._draw_bar)
        self._tc.bind('<Button-1>',  self._drag_start)
        self._tc.bind('<B1-Motion>', self._drag_move)

        self.content = tk.Frame(self, bg=self.WIN_BG)
        self.content.pack(fill=tk.BOTH, expand=True, padx=3, pady=(0, 3))
        self.transient(parent)
        self.grab_set()

    def _draw_bar(self, e=None):
        tc = self._tc
        w, h = tc.winfo_width(), self.BAR_H
        if w < 4:
            return
        tc.delete('all')
        # Three-stop gradient: deep navy → royal → slightly deeper
        mid = h * 55 // 100
        fill_gradient(tc, 0, 0,   w, mid, '#081a42', '#1a6ac8', steps=mid)
        fill_gradient(tc, 0, mid, w, h,   '#1a6ac8', '#0e4898', steps=h - mid)
        # Chrome shine lines
        tc.create_line(0, 0, w, 0, fill='#60b8ff', width=2)
        tc.create_line(0, 2, w, 2, fill='#1e80d8', width=1)
        tc.create_line(0, h-1, w, h-1, fill='#040e22', width=1)
        # Title (shadow + bright)
        shadow_text(tc, 10, h//2, text=self._title_text, anchor='w',
                    fill='white', font=('Tahoma', 9, 'bold'))
        # Close button
        bx1, by1, bx2, by2 = w-28, 4, w-5, h-4
        tc.create_rectangle(bx1, by1, bx2, by2,
                             fill='#bb1f1f', outline='#6e0c0c',
                             tags=('cbtn', 'crect'))
        tc.create_line(bx1+1, by1+1, bx2-1, by1+1,
                       fill='#ee6666', width=1, tags='cbtn')
        tc.create_text((bx1+bx2)//2, (by1+by2)//2, text='✕',
                       fill='white', font=('Tahoma', 8, 'bold'), tags='cbtn')
        tc.tag_bind('cbtn', '<Button-1>', lambda ev: self.destroy())
        tc.tag_bind('cbtn', '<Enter>',
                    lambda ev: tc.itemconfig('crect', fill='#e03030'))
        tc.tag_bind('cbtn', '<Leave>',
                    lambda ev: tc.itemconfig('crect', fill='#bb1f1f'))

    def _drag_start(self, e):
        self._ox = e.x_root - self.winfo_x()
        self._oy = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f'+{e.x_root-self._ox}+{e.y_root-self._oy}')


def os_button(parent, text, command, **kw):
    """Standard OS-style raised button."""
    kw.setdefault('font',             ('Tahoma', 9))
    kw.setdefault('bg',               '#d8d4c6')
    kw.setdefault('fg',               '#000000')
    kw.setdefault('relief',           tk.RAISED)
    kw.setdefault('bd',               2)
    kw.setdefault('activebackground', '#eae6d8')
    kw.setdefault('cursor',           'hand2')
    kw.setdefault('padx',             8)
    return tk.Button(parent, text=text, command=command, **kw)

# ─── Login Logic ──────────────────────────────────────────────────────────────
def check_computer_login():
    """Validates the main computer lock screen password."""
    if comp_pass_entry.get().strip().lower() == COMP_PASSWORD:
        show_desktop()
    else:
        messagebox.showerror("Access Denied", "Incorrect Password.")
        comp_pass_entry.delete(0, tk.END)

def open_dummy_file(filename):
    """Simulates opening generic files to distract players."""
    messagebox.showinfo(filename,
        f"Document Empty.\nNo student record modifications found in {filename}.")

# ─── Grade Portal ─────────────────────────────────────────────────────────────
def open_grade_portal():
    """Creates the secure login gate for the grade portal."""
    win = StyledWindow(root, "Secure Database Gateway", 430, 270)
    tk.Label(win.content, text="🔒  ENCRYPTED PORTAL",
             font=('Tahoma', 14, 'bold'), fg='#a01818',
             bg=win.WIN_BG).pack(pady=(18, 4))
    tk.Label(win.content, text="Enter Database Encryption Key:",
             font=('Tahoma', 10), bg=win.WIN_BG).pack()
    entry = tk.Entry(win.content, font=('Tahoma', 12), show="●",
                     justify="center", relief=tk.FLAT, bd=0,
                     bg='white', width=22,
                     highlightthickness=2,
                     highlightbackground='#4a88d8',
                     highlightcolor='#6ab0ff')
    entry.pack(pady=12)
    entry.focus_set()

    def verify():
        if entry.get().strip().lower() == PORTAL_PASSWORD:
            win.destroy()
            show_grade_modifier_interface()
        else:
            messagebox.showerror("Security Alert",
                                 "Invalid Encryption Key. Access Denied.")
            entry.delete(0, tk.END)

    win.bind('<Return>', lambda e: verify())
    os_button(win.content, "  Authenticate  ", verify,
              font=('Tahoma', 10, 'bold')).pack(pady=6)


def show_grade_modifier_interface():
    """The actual puzzle interface where grades are manipulated."""
    win = StyledWindow(root, "District Grade Management System v4.2", 510, 440)
    tk.Label(win.content, text="Student Record: Alex Mercer",
             font=('Tahoma', 14, 'bold'), fg='#6b4500',
             bg=win.WIN_BG).pack(pady=12)
    tk.Frame(win.content, bg='#b8a888', height=1).pack(fill=tk.X, padx=15, pady=2)

    dropdowns = {}
    for subject in student_grades:
        row = tk.Frame(win.content, bg=win.WIN_BG)
        row.pack(pady=9)
        tk.Label(row, text=f"{subject}:", font=('Tahoma', 12),
                 bg=win.WIN_BG, width=12, anchor='e').pack(side=tk.LEFT, padx=6)
        var = tk.StringVar(value="F")
        opt = tk.OptionMenu(row, var, "A", "B", "C", "D", "F")
        opt.config(font=('Tahoma', 11), width=4,
                   bg='#d8d4c6', fg='#000000', relief=tk.RAISED, bd=2)
        opt.pack(side=tk.LEFT)
        dropdowns[subject] = var

    tk.Frame(win.content, bg='#b8a888', height=1).pack(fill=tk.X, padx=15, pady=8)

    def submit_grades():
        if all(dropdowns[s].get() == "A" for s in student_grades):
            messagebox.showinfo("Database Sync",
                "Changes committed successfully. Permanent records overwritten.")
            win.destroy()
            trigger_win_condition()
        else:
            messagebox.showerror("Sync Failed",
                "Error: Student GPA remains below passing threshold.")

    os_button(win.content, "  Commit Changes to Server  ", submit_grades,
              font=('Tahoma', 11, 'bold'),
              bg='#246e28', fg='white',
              activebackground='#2e8832',
              activeforeground='white').pack(pady=4)

# ─── Win Condition ────────────────────────────────────────────────────────────
def trigger_win_condition():
    """Unlocks the door and displays the final win graphic."""
    for w in root.winfo_children():
        w.destroy()
    root.configure(bg='#000000')
    SW = root.winfo_screenwidth()
    SH = root.winfo_screenheight()
    c = tk.Canvas(root, bg='#000000', highlightthickness=0)
    c.pack(fill=tk.BOTH, expand=True)
    fill_gradient(c, 0, 0, SW, SH, '#000000', '#061206', steps=80)
    # Matrix rain dots
    rng2 = random.Random(7)
    for _ in range(120):
        c.create_text(rng2.randint(0, SW), rng2.randint(0, SH),
                      text=rng2.choice('01'), fill='#003300',
                      font=('Courier New', 10))
    shadow_text(c, SW//2, SH//2-50, text="SYSTEM OVERRIDE",
                font=('Courier New', 44, 'bold'), fill='#00ff41')
    shadow_text(c, SW//2, SH//2+30, text="EXIT DOOR UNLOCKED",
                font=('Courier New', 30), fill='#00cc33')
    door_lock.on()

# ─── Desktop Cloud Helper ─────────────────────────────────────────────────────
def draw_cloud(c, cx, cy, sz):
    """Draw a fluffy cloud from overlapping white ovals."""
    puffs = [
        ( 0,     0,     sz,     sz//2),
        (-sz//2, sz//5, sz*2//3, sz*2//5),
        ( sz//2, sz//5, sz*2//3, sz*2//5),
        ( 0,    -sz//3, sz//2,   sz//3),
    ]
    # Shadow
    c.create_oval(cx-sz, cy+sz//4, cx+sz, cy+sz//2+6,
                  fill='#c0dcee', outline='')
    for dx, dy, rx, ry in puffs:
        c.create_oval(cx+dx-rx, cy+dy-ry, cx+dx+rx, cy+dy+ry,
                      fill='white', outline='')

# ─── Clock ────────────────────────────────────────────────────────────────────
def update_clock(label):
    try:
        label.config(text=datetime.now().strftime(" %I:%M %p "))
        label.after(10_000, lambda: update_clock(label))
    except tk.TclError:
        pass

# ─── Desktop ─────────────────────────────────────────────────────────────────
def show_desktop():
    """Clear lock screen and build the EduOS desktop."""
    for w in root.winfo_children():
        w.destroy()

    SW     = root.winfo_screenwidth()
    SH     = root.winfo_screenheight()
    TBAR_H = 44
    DH     = SH - TBAR_H

    # ── Taskbar as Canvas (enables gradient) ──────────────────────────────────
    tb = tk.Canvas(root, height=TBAR_H, highlightthickness=0)
    tb.pack(side=tk.BOTTOM, fill=tk.X)

    fill_gradient(tb, 0, 0, SW, TBAR_H, '#c8c8c8', '#f0f0f0', steps=TBAR_H)
    tb.create_line(0, 0, SW, 0, fill='#ffffff', width=2)
    tb.create_line(0, 2, SW, 2, fill='#b0b0b0', width=1)

    # Start button: gradient Canvas with hover redraw
    SBW, SBH = 94, 34
    sb = tk.Canvas(tb, width=SBW, height=SBH,
                   highlightthickness=1, highlightbackground='#186018',
                   cursor='hand2')

    def draw_start(hover=False):
        sb.delete('all')
        c1 = '#3eb83e' if hover else '#30a030'
        c2 = '#76d876' if hover else '#5ec85e'
        mid = SBH * 55 // 100
        fill_gradient(sb, 0, 0,   SBW, mid, c1, c2, steps=mid)
        fill_gradient(sb, 0, mid, SBW, SBH, c2,
                      lerp_color(c1, '#187018', 0.35), steps=SBH - mid)
        sb.create_line(1, 1, SBW-1, 1, fill='#98e898', width=1)
        sb.create_text(SBW//2, SBH//2, text="⊞  Start",
                       fill='white', font=('Tahoma', 10, 'bold'))

    draw_start()
    sb.bind('<Enter>', lambda e: draw_start(True))
    sb.bind('<Leave>', lambda e: draw_start(False))
    tb.create_window(6, TBAR_H//2, window=sb, anchor='w')

    # System tray clock
    clk = tk.Label(tb, font=('Tahoma', 9), bg='#c0c0c0',
                   fg='#000000', relief=tk.SUNKEN, bd=1, padx=4)
    tb.create_window(SW - 6, TBAR_H//2, window=clk, anchor='e')
    update_clock(clk)

    # ── Wallpaper Canvas ───────────────────────────────────────────────────────
    wc = tk.Canvas(root, highlightthickness=0)
    wc.pack(fill=tk.BOTH, expand=True)

    sky_h    = int(DH * 0.56)
    haze_h   = int(DH * 0.10)
    hill_y   = sky_h + haze_h
    hill2_y  = int(DH * 0.74)
    cloud_y  = int(sky_h * 0.62)

    # Sky: deep azure → pale ice blue
    fill_gradient(wc, 0, 0,       SW, sky_h,  '#1872cc', '#9ad4f0', steps=140)
    # Haze / horizon band
    fill_gradient(wc, 0, sky_h,   SW, hill_y, '#9ad4f0', '#c4eec4', steps=40)
    # Back hills (softer, distant green)
    fill_gradient(wc, 0, hill_y,  SW, hill2_y,'#78cc78', '#48aa48', steps=50)
    # Front hills (vivid emerald)
    fill_gradient(wc, 0, hill2_y, SW, DH,     '#38b038', '#18601a', steps=140)

    # Organic hill humps along the back-hill transition
    rng = random.Random(42)
    for i in range(10):
        hx = int(SW * (i + 0.5) / 10)
        hr = rng.randint(55, 115)
        hy = hill_y + rng.randint(-18, 12)
        wc.create_oval(hx-hr, hy-22, hx+hr, hy+45,
                       fill='#78cc78', outline='')

    # Sun (upper right of sky)
    sx, sy = int(SW * 0.80), int(sky_h * 0.21)
    # Outer glow layers (stippled)
    wc.create_oval(sx-95, sy-95, sx+95, sy+95,
                   fill='#fff6a0', outline='', stipple='gray12')
    wc.create_oval(sx-70, sy-70, sx+70, sy+70,
                   fill='#ffee66', outline='', stipple='gray25')
    wc.create_oval(sx-52, sy-52, sx+52, sy+52,
                   fill='#ffee44', outline='', stipple='gray50')
    # Sun disc
    wc.create_oval(sx-36, sy-36, sx+36, sy+36,
                   fill='#ffffcc', outline='#ffe566', width=2)
    wc.create_oval(sx-32, sy-32, sx+32, sy+32, fill='#fffff0', outline='')
    wc.create_oval(sx-16, sy-16, sx+16, sy+16, fill='#ffffff', outline='')

    # Cloud layer
    cloud_positions = [
        (int(SW*0.12), cloud_y - 25, 52),
        (int(SW*0.30), cloud_y + 10, 38),
        (int(SW*0.46), cloud_y - 8,  62),
        (int(SW*0.60), cloud_y + 18, 42),
        (int(SW*0.40), cloud_y - 30, 30),
    ]
    for cx, cy, sz in cloud_positions:
        draw_cloud(wc, cx, cy, sz)

    # OS watermark
    shadow_text(wc, SW-18, 15, text="EduOS Professional",
                font=('Tahoma', 13, 'italic'), fill='white', anchor='ne')

    # ── Desktop Icons ──────────────────────────────────────────────────────────
    icon_defs = [
        ("📁", "School\nBudget.xlsx",  lambda: open_dummy_file("School_Budget.xlsx")),
        ("📄", "Suspension\nList.pdf", lambda: open_dummy_file("Suspension_List.pdf")),
        ("📝", "Detention\nLogs.txt",  lambda: open_dummy_file("Detention_Logs.txt")),
        ("🌐", "Grade\nPortal",        open_grade_portal),
    ]

    for i, (ico, name, cmd) in enumerate(icon_defs):
        iy = 20 + i * 102
        # Compute approximate wallpaper color at this y for blending
        if iy < sky_h:
            bg_c = lerp_color('#1872cc', '#9ad4f0', iy / sky_h)
        elif iy < hill_y:
            bg_c = lerp_color('#9ad4f0', '#c4eec4', (iy-sky_h) / max(hill_y-sky_h, 1))
        elif iy < hill2_y:
            bg_c = lerp_color('#78cc78', '#48aa48', (iy-hill_y) / max(hill2_y-hill_y, 1))
        else:
            bg_c = lerp_color('#38b038', '#18601a', (iy-hill2_y) / max(DH-hill2_y, 1))

        hover_bg = lerp_color(bg_c, '#2244bb', 0.55)

        ib = tk.Button(wc, text=ico, font=('Helvetica', 26),
                       bg=bg_c, fg='#111111', relief=tk.FLAT, bd=0,
                       activebackground=hover_bg,
                       cursor='hand2', command=cmd)
        wc.create_window(52, iy+28, window=ib, width=70, height=56)
        ib.bind('<Enter>', lambda e, b=ib, h=hover_bg:
                b.config(bg=h, relief=tk.GROOVE, bd=1))
        ib.bind('<Leave>', lambda e, b=ib, g=bg_c:
                b.config(bg=g, relief=tk.FLAT, bd=0))

        # White pill background behind label so black text is legible
        # over any wallpaper color
        nl = tk.Label(wc, text=name, font=('Tahoma', 8),
                      bg='#ffffff', fg='#111111', justify=tk.CENTER,
                      relief=tk.FLAT, bd=0, padx=2)
        wc.create_window(52, iy+76, window=nl, width=86)
        nl.bind('<Button-1>',        lambda e, c=cmd: c())
        nl.bind('<Double-Button-1>', lambda e, c=cmd: c())


# ─── Main Window + Lock Screen ────────────────────────────────────────────────
root = tk.Tk()
root.title("EduOS Professional")
root.attributes('-fullscreen', True)
root.configure(bg='#020c1e')

SW = root.winfo_screenwidth()
SH = root.winfo_screenheight()

# Background canvas
bg = tk.Canvas(root, highlightthickness=0, bg='#020c1e')
bg.pack(fill=tk.BOTH, expand=True)

# Deep midnight gradient (top half down, bottom half up = darker at edges)
fill_gradient(bg, 0, 0,       SW, SH*55//100, '#020c1e', '#0d2858', steps=140)
fill_gradient(bg, 0, SH*55//100, SW, SH,      '#0d2858', '#020c1e', steps=110)

# ── Star field ────────────────────────────────────────────────────────────────
rng = random.Random(77)
for _ in range(220):
    sx2 = rng.randint(0, SW)
    sy2 = rng.randint(68, int(SH * 0.64))
    sz2 = rng.choice([1, 1, 1, 1, 2])
    br  = rng.randint(130, 255)
    tint = rng.choice(['white', 'white', 'white', '#aaddff', '#ffeebb', '#ddffdd'])
    bg.create_oval(sx2, sy2, sx2+sz2, sy2+sz2, fill=tint, outline='')

# ── Brand bar ─────────────────────────────────────────────────────────────────
BRAND_H = 64
fill_gradient(bg, 0, 0, SW, BRAND_H, '#010818', '#0c2050', steps=BRAND_H)
bg.create_line(0, BRAND_H,   SW, BRAND_H,   fill='#2470c8', width=2)
bg.create_line(0, BRAND_H+2, SW, BRAND_H+2, fill='#081428', width=1)

# Logo glow + text
bg.create_text(34, 32, text="EduOS",
               font=('Tahoma', 26, 'bold italic'), fill='#003888', anchor='w')
bg.create_text(32, 31, text="EduOS",
               font=('Tahoma', 26, 'bold italic'), fill='#48ccff', anchor='w')
bg.create_text(154, 38, text="Professional",
               font=('Tahoma', 12, 'italic'), fill='#5888aa', anchor='w')
shadow_text(bg, SW//2, 31, text="Principal's Workstation",
            font=('Tahoma', 12), fill='#88c0e8', anchor='center')

# ── Panel geometry ────────────────────────────────────────────────────────────
pw, ph   = 376, 328
px       = (SW - pw) // 2
py       = SH // 2 - ph // 2 - 10

# Welcome instruction
shadow_text(bg, SW//2, py-26,
            text="To begin, enter your password and click  →",
            font=('Tahoma', 12), fill='#70a8d8')

# Horizontal rules above/below panel
for rule_y in (py-46, py+ph+18):
    bg.create_line(0, rule_y,   SW, rule_y,   fill='#0c2848', width=1)
    bg.create_line(0, rule_y+1, SW, rule_y+1, fill='#1a4070', width=1)

# ── User card glow + body ─────────────────────────────────────────────────────
glow_rect(bg, px, py, px+pw, py+ph, '#1878cc')
# Bright border
bg.create_rectangle(px-2, py-2, px+pw+2, py+ph+2, fill='#2e7ec8', outline='')
# Card gradient body
fill_gradient(bg, px, py, px+pw, py+ph, '#0c2258', '#07163a', steps=70)
# Top shine
bg.create_line(px+1, py+1, px+pw-1, py+1, fill='#2858a0', width=2)
bg.create_line(px+1, py+2, px+pw-1, py+2, fill='#102040', width=1)

# Avatar strip (lighter band at top of card)
bg.create_rectangle(px+1, py+1, px+pw-1, py+108, fill='#0e2862', outline='')
bg.create_line(px+1, py+108, px+pw-1, py+108, fill='#163c78', width=1)

# Avatar
bg.create_text(SW//2, py+60, text="👤", font=('Helvetica', 54), fill='#70aad8')

# Username (shadow + bright)
shadow_text(bg, SW//2, py+124, text="Principal",
            font=('Tahoma', 17, 'bold'), fill='white')

# Thin rule under name
bg.create_line(px+50, py+142, px+pw-50, py+142, fill='#1e4880', width=1)

# ── Password entry ────────────────────────────────────────────────────────────
comp_pass_entry = tk.Entry(bg, font=('Tahoma', 13), show="●",
                           justify="center", relief=tk.FLAT, bd=0,
                           bg='#d0e4f8', insertbackground='#1c5aaa',
                           width=18,
                           highlightthickness=2,
                           highlightbackground='#3a78c0',
                           highlightcolor='#58aaff')
bg.create_window(SW//2, py+170, window=comp_pass_entry,
                 width=222, height=30)
comp_pass_entry.focus_set()

# ── Gradient arrow login button ───────────────────────────────────────────────
BW, BH = 54, 30

def make_login_btn():
    lb = tk.Canvas(bg, width=BW, height=BH,
                   highlightthickness=1, highlightbackground='#0e50c0',
                   cursor='hand2')

    def draw_lb(hover=False):
        lb.delete('all')
        c1 = '#1e88e8' if hover else '#1460c0'
        c2 = '#60b4f8' if hover else '#3e96e0'
        fill_gradient(lb, 0, 0, BW, BH, c1, c2, steps=BH)
        lb.create_line(1, 1, BW-1, 1, fill='#98d0ff', width=1)
        lb.create_text(BW//2, BH//2, text="→",
                       fill='white', font=('Tahoma', 14, 'bold'))

    draw_lb()
    lb.bind('<Enter>',    lambda e: draw_lb(True))
    lb.bind('<Leave>',    lambda e: draw_lb(False))
    lb.bind('<Button-1>', lambda e: check_computer_login())
    bg.create_window(SW//2, py+215, window=lb)

make_login_btn()

# "or press Enter" hint
bg.create_text(SW//2, py+248, text="or press Enter",
               font=('Tahoma', 8, 'italic'), fill='#3a6a9a')

# ── Bottom status bar ─────────────────────────────────────────────────────────
fill_gradient(bg, 0, SH-48, SW, SH, '#010818', '#040e24', steps=48)
bg.create_line(0, SH-48, SW, SH-48, fill='#163054', width=1)
shadow_text(bg, SW//2, SH-24,
            text="Press Ctrl+Alt+Del to unlock  •  EduOS Professional Edition",
            font=('Tahoma', 9), fill='#4070a8')

# ─── Key Bindings ─────────────────────────────────────────────────────────────
root.bind('<Return>',                lambda e: check_computer_login())
root.bind('<Control-Option-Escape>', gm_backdoor_trigger)

root.mainloop()
