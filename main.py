import tkinter as tk
from tkinter import messagebox
import time, random
from datetime import datetime
import os as _os
import sys as _sys
try:
    from PIL import Image as _PILImage, ImageTk as _PILImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# ─── GPIO — real on Raspberry Pi, simulated everywhere else ──────────────────
RELAY_PIN = 18          # BCM pin number wired to the maglock relay

class MockGPIO:
    """Fallback used on non-Pi platforms (macOS, Windows, etc.)."""
    def __init__(self, pin, active_high=False, initial_value=False):
        self.pin = pin
        print(f"[MOCK] Simulated relay initialised on BCM Pin {pin}")
    def on(self):
        print("\n" + "="*50)
        print("[HARDWARE] Maglock Released! Exit Door Unlocked.")
        print("="*50 + "\n")
    def off(self):
        print(f"[MOCK] Pin {self.pin} → OFF")
    def close(self):
        pass

try:
    # pyrefly: ignore [missing-import]
    from gpiozero import OutputDevice
    door_lock = OutputDevice(RELAY_PIN, active_high=True, initial_value=False)
    print(f"[GPIO] Real relay on BCM pin {RELAY_PIN} — running on Raspberry Pi")
except Exception as _gpio_err:
    print(f"[GPIO] gpiozero not available ({_gpio_err}). Using mock.")
    door_lock = MockGPIO(RELAY_PIN)

# ─── Config ───────────────────────────────────────────────────────────────────
COMP_PASSWORD    = "admin"
PORTAL_PASSWORD  = "override"
portal_attempts  = 0
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

reset_timestamps = []

def gm_reset_trigger(event):
    """Hold Control+Option/Alt, tap R 3× quickly (< 1.5 s) to restart the game process."""
    global reset_timestamps
    current_time = time.time()
    reset_timestamps.append(current_time)
    if len(reset_timestamps) > 3:
        reset_timestamps.pop(0)
    if len(reset_timestamps) == 3:
        if reset_timestamps[2] - reset_timestamps[0] < 1.5:
            print("[GM] Reset backdoor triggered successfully. Restarting game...")
            # 1. Relock the door maglock
            door_lock.off()
            # 2. Spawn a completely fresh process asynchronously
            import subprocess as _subprocess
            python = _sys.executable
            _subprocess.Popen([python] + _sys.argv)
            # 3. Cleanly exit the current program
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
        if _sys.platform != 'darwin':
            self.grab_set()
        # Force OS-level keyboard focus on the correct widget so global shortcuts work
        self.after(100, self._auto_focus)
        self.bind('<Button-1>', lambda e: self._auto_focus())

    def _auto_focus(self, event=None):
        try:
            curr = self.focus_get()
            if curr and curr != self:
                curr.focus_force()
            else:
                self.focus_force()
        except Exception:
            self.focus_force()

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
    """XP-style gradient canvas button, styled like the Start button."""
    font      = kw.pop('font',   ('Tahoma', 9, 'bold'))
    fg        = kw.pop('fg',     'white')
    base_c1   = kw.pop('bg',     '#1460c0')          # top colour
    base_c2   = kw.pop('activebackground', '#3e96e0') # hover top colour
    hi_border = kw.pop('highlightbackground', '#0e50c0')
    # ignore any leftover tk.Button-only kwargs that don't apply to Canvas
    for _drop in ('activeforeground', 'relief', 'bd', 'padx', 'pady'):
        kw.pop(_drop, None)

    # Measure text to size the canvas
    tmp = tk.Label(parent, text=text, font=font)
    tmp.update_idletasks()
    tw = tmp.winfo_reqwidth() + 20
    th = tmp.winfo_reqheight() + 8
    tmp.destroy()
    BW, BH = max(tw, 80), max(th, 26)

    # Derive hover colours by lightening base a little
    def _lighten(hex_c, amt=0.25):
        r, g, b = hex_rgb(hex_c)
        return '#{:02x}{:02x}{:02x}'.format(
            min(255, int(r + (255-r)*amt)),
            min(255, int(g + (255-g)*amt)),
            min(255, int(b + (255-b)*amt)))

    hover_c1 = _lighten(base_c1, 0.25)
    hover_c2 = _lighten(base_c2, 0.25)

    btn = tk.Canvas(parent, width=BW, height=BH,
                    highlightthickness=1,
                    highlightbackground=hi_border,
                    cursor='hand2', **kw)

    def _draw(hover=False):
        btn.delete('all')
        c1 = hover_c1 if hover else base_c1
        c2 = hover_c2 if hover else base_c2
        mid = BH * 55 // 100
        fill_gradient(btn, 0, 0,   BW, mid, c1, c2, steps=mid)
        fill_gradient(btn, 0, mid, BW, BH,  c2,
                      lerp_color(c1, _lighten(c1, -0.15), 0.45),
                      steps=BH - mid)
        # Top chrome shine
        btn.create_line(1, 1, BW-1, 1,
                        fill=_lighten(c2, 0.35), width=1)
        btn.create_text(BW//2, BH//2, text=text,
                        fill=fg, font=font)

    _draw()
    btn.bind('<Enter>',    lambda e: _draw(True))
    btn.bind('<Leave>',    lambda e: _draw(False))
    btn.bind('<Button-1>', lambda e: command())
    return btn

# ─── Login Logic ──────────────────────────────────────────────────────────────
def check_computer_login():
    """Validates the main computer lock screen password."""
    if comp_pass_entry.get().strip().lower() == COMP_PASSWORD:
        show_desktop()
    else:
        bg.itemconfig(login_error_text, text="⚠️  Access Denied: Incorrect Password.")
        comp_pass_entry.delete(0, tk.END)
        comp_pass_entry.focus_set()

# ─── School Budget Viewer ────────────────────────────────────────────────────
def open_school_budget():
    """Displays a fake-but-funny school budget spreadsheet."""
    win = StyledWindow(root, "School_Budget.xlsx — Microsoft Excel", 672, 760)

    tk.Label(win.content,
             text="LEGS Academy — Annual Operating Budget FY 2024-25",
             font=('Tahoma', 15, 'bold'), fg='#1a1a6e', bg=win.WIN_BG
             ).pack(pady=(10, 2))
    tk.Label(win.content,
             text="Prepared by: Mr. Wigglesworth, Finance & Cheese Committee",
             font=('Tahoma', 12, 'italic'), fg='#555555', bg=win.WIN_BG
             ).pack(pady=(0, 6))

    # Column definitions: (header text, char-width, anchor)
    COL_DEFS = [("Category", 22), ("Budgeted ($)", 11), ("Actual ($)", 11), ("Notes", 28)]
    FONT_HDR  = ('Courier New', 12, 'bold')
    FONT_ROW  = ('Courier New', 12)
    FONT_TOT  = ('Courier New', 12, 'bold')

    # Spreadsheet header row
    hdr_frame = tk.Frame(win.content, bg='#1a3a8a')
    hdr_frame.pack(fill=tk.X, padx=10)
    for col, w in COL_DEFS:
        tk.Label(hdr_frame, text=col, font=FONT_HDR,
                 fg='white', bg='#1a3a8a', width=w, anchor='w',
                 relief=tk.FLAT, bd=0).pack(side=tk.LEFT, padx=2, pady=3)

    rows = [
        ("Teacher Salaries",          "412,000", "412,001", "Overspent by $1. Sorry, Mrs. Plum."),
        ("Chalk & Dry-Erase Markers", "  1,200", "  4,800", "Someone drew a T-Rex on EVERYTHING"),
        ("Emergency Pizza Fund",       "  3,500", "  3,499", "One slice left. Principal ate it."),
        ("Library Books",             "  8,000", "  7,998", "2 books missing. Still blaming Jake."),
        ("Gym Equipment",             "  6,200", " 12,400", "Accidentally bought a trampoline"),
        ("Science Supplies",          "  4,000", " 14,000", "Who approved the volcano THAT big?"),
        ("Cafeteria: Mystery Meat",   " 22,000", " 22,000", "Still a mystery. Do not investigate."),
        ("Cafeteria: Chocolate Milk", "  5,500", " 11,200", "Kids negotiated a SECOND milk break"),
        ("School Nurse Supplies",     "  2,800", "  4,100", "Mostly bandaids. So many bandaids."),
        ("IT & Computers",            " 15,000", " 15,043", "$43 on screensaver of a fish tank"),
        ("Janitorial Services",       " 18,000", " 18,000", "Heroes. True unsung heroes."),
        ("Art Dept: Glitter",         "    200", "  3,200", "It's EVERYWHERE. We cannot stop it."),
        ("School Mascot Costume",     "    800", "  2,700", "3rd one this year. Bears bite."),
        ("Fire Extinguishers",        "    400", "  1,600", "Chemistry class. 'Nuff said."),
        ("Principal's Stress Balls",  "     50", "    420", "Ordering in bulk now."),
        ("TOTAL",                     "499,650", "532,961", "↑ We are so grounded."),
    ]

    # Plain frame — fills dialog, no scroll bar needed at this size
    table_frame = tk.Frame(win.content, bg=win.WIN_BG)
    table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)

    # NOTES_WRAP_PX: pixel budget for the Notes column at Courier 12 on macOS.
    # (dialog width 672 − 2×10 padding − approx widths of cat/bud/act columns)
    NOTES_WRAP_PX = 220

    for idx, (cat, bud, act, note) in enumerate(rows):
        row_bg = '#e8eef8' if idx % 2 == 0 else '#f5f5f5'
        is_total = cat == 'TOTAL'
        if is_total:
            row_bg = '#c8d8f8'
        rf = tk.Frame(table_frame, bg=row_bg)
        rf.pack(fill=tk.X)
        font_style = FONT_TOT if is_total else FONT_ROW
        fg_col = '#8b0000' if is_total else '#111111'

        # Fixed-width columns: Category, Budgeted, Actual
        for val, (_, w) in zip([cat, bud, act], COL_DEFS[:3]):
            tk.Label(rf, text=val, font=font_style, fg=fg_col,
                     bg=row_bg, width=w, anchor='w', relief=tk.FLAT, bd=0
                     ).pack(side=tk.LEFT, padx=2, pady=2)

        # Notes column: no fixed char-width, wraps at pixel boundary instead
        tk.Label(rf, text=note, font=font_style, fg=fg_col,
                 bg=row_bg, anchor='w', justify=tk.LEFT,
                 wraplength=NOTES_WRAP_PX, relief=tk.FLAT, bd=0
                 ).pack(side=tk.LEFT, padx=2, pady=2, fill=tk.X, expand=True)

    footer = tk.Label(win.content,
                      text="⚠  CONFIDENTIAL  •  Do not share with students or the cheese committee",
                      font=('Tahoma', 11, 'italic'), fg='#888888', bg=win.WIN_BG)
    footer.pack(pady=(4, 8))


# ─── Suspension List Viewer ───────────────────────────────────────────────────
def open_suspension_list():
    """Displays a fake suspension list PDF viewer with humorous entries."""
    win = StyledWindow(root, "Suspension_List.pdf — Adobe Acrobat Reader", 836, 760)

    # PDF toolbar mock
    toolbar = tk.Frame(win.content, bg='#4a4a4a', height=28)
    toolbar.pack(fill=tk.X)
    toolbar.pack_propagate(False)
    for lbl in ["File", "Edit", "View", "Tools", "Help"]:
        tk.Label(toolbar, text=lbl, font=('Tahoma', 14), fg='#dddddd',
                 bg='#4a4a4a', padx=6).pack(side=tk.LEFT)
    tk.Label(toolbar, text="Page: 1 / 1", font=('Tahoma', 14),
             fg='#dddddd', bg='#4a4a4a').pack(side=tk.RIGHT, padx=8)

    # PDF body
    pdf_frame = tk.Frame(win.content, bg='#888888', pady=10)
    pdf_frame.pack(fill=tk.BOTH, expand=True)

    page = tk.Frame(pdf_frame, bg='white',
                    highlightthickness=1, highlightbackground='#555555')
    page.pack(padx=20, pady=8, fill=tk.BOTH, expand=True)

    tk.Label(page, text="LEGS ACADEMY", font=('Georgia', 20, 'bold'),
             fg='#1a1a6e', bg='white').pack(pady=(14, 0))
    tk.Label(page, text="OFFICIAL SUSPENSION REGISTER — 2024-25 School Year",
             font=('Georgia', 15, 'bold'), fg='#1a1a6e', bg='white').pack()
    tk.Frame(page, bg='#1a1a6e', height=2).pack(fill=tk.X, padx=20, pady=6)

    # Column character-widths for fixed columns; Reason fills remaining space
    FIXED_HDRS   = ["#", "Student Name", "Grade", "Date"]
    FIXED_WIDTHS = [3,    20,              6,       10   ]
    HDR_FONT     = ('Courier New', 13, 'bold')
    BODY_FONT    = ('Courier New', 13)
    REASON_WRAP  = 390   # pixel budget for the Reason column

    hrow = tk.Frame(page, bg='#1a1a6e')
    hrow.pack(fill=tk.X, padx=20)
    for h, w in zip(FIXED_HDRS, FIXED_WIDTHS):
        tk.Label(hrow, text=h, font=HDR_FONT,
                 fg='white', bg='#1a1a6e', width=w, anchor='w'
                 ).pack(side=tk.LEFT)
    # Pack Days to the RIGHT first so Reason can fill the space in-between
    tk.Label(hrow, text="Days", font=HDR_FONT,
             fg='white', bg='#1a1a6e', width=5, anchor='w'
             ).pack(side=tk.RIGHT)
    tk.Label(hrow, text="Reason", font=HDR_FONT,
             fg='white', bg='#1a1a6e', anchor='w'
             ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    entries = [
        ("01", "Tyler Pranksworth",   "7th", "Sep 04", "Released 47 frogs into gym during assembly",          "3"),
        ("02", "Cody McSneeze",       "6th", "Sep 12", "Sneezed on the science fair. On purpose.",             "1"),
        ("03", "Emma Giggleston",     "8th", "Sep 19", "Convinced half the class that Thursday was cancelled", "2"),
        ("04", "Jake 'The Vault' Kim","7th", "Oct 02", "Ate 11 lunches in one day (his own + others)",         "1"),
        ("05", "Sophie Bananapeels",  "6th", "Oct 15", "Booby-trapped the principal's chair with a whoopee",  "2"),
        ("06", "Marcus Loudmouth",    "8th", "Nov 01", "Held unofficial 'burp contest' during math quiz",      "1"),
        ("07", "Tyler Pranksworth",   "7th", "Nov 08", "Glued ALL the chairs to the ceiling (don't ask)",     "5"),
        ("08", "Zoe Klutzenburg",     "6th", "Nov 22", "Knocked over the entire school trophy cabinet. Twice.","1"),
        ("09", "Benny Noodlestir",    "7th", "Dec 04", "Microwaved fish in the teacher's lounge at 7 AM",     "2"),
        ("10", "Tyler Pranksworth",   "7th", "Jan 13", "See files #1 and #7. Tyler knows what he did.",        "5"),
        ("11", "Lily Butterfingers",  "6th", "Feb 06", "Slipped on own banana peel. Blamed school. Sued.",    "0*"),
        ("12", "Noah Loudsnore",      "8th", "Mar 01", "Fell asleep in gym, snored so loud class was dismissed","1"),
    ]

    # Plain frame — dialog is tall enough to show all rows without scrolling
    rows_frame = tk.Frame(page, bg='white')
    rows_frame.pack(fill=tk.X, padx=20, pady=4)

    for idx, (num, name, grade, date, reason, days) in enumerate(entries):
        row_bg = '#f0f4ff' if idx % 2 == 0 else 'white'
        rf = tk.Frame(rows_frame, bg=row_bg)
        rf.pack(fill=tk.X)
        # Fixed-width columns: #, Name, Grade, Date
        for val, w in zip([num, name, grade, date], FIXED_WIDTHS):
            tk.Label(rf, text=val, font=BODY_FONT, fg='#111111',
                     bg=row_bg, width=w, anchor='nw', relief=tk.FLAT, bd=0
                     ).pack(side=tk.LEFT, pady=2)
        # Days on the right (mirrors header)
        tk.Label(rf, text=days, font=BODY_FONT, fg='#111111',
                 bg=row_bg, width=5, anchor='nw', relief=tk.FLAT, bd=0
                 ).pack(side=tk.RIGHT, pady=2)
        # Reason fills remaining width and wraps as needed
        tk.Label(rf, text=reason, font=BODY_FONT, fg='#111111',
                 bg=row_bg, anchor='nw', justify=tk.LEFT, relief=tk.FLAT, bd=0,
                 wraplength=REASON_WRAP
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, pady=2)

    tk.Frame(page, bg='#1a1a6e', height=1).pack(fill=tk.X, padx=20, pady=(6, 2))
    tk.Label(page, text="* Case still pending. Lily's lawyer is a 6th grader.",
             font=('Courier New', 13, 'italic'), fg='#888888', bg='white').pack()
    tk.Label(page, text="CONFIDENTIAL — Disciplinary Records — Not for Distribution",
             font=('Tahoma', 13, 'italic'), fg='#aaaaaa', bg='white').pack(pady=(0, 8))


# ─── Detention Log Viewer ─────────────────────────────────────────────────────
def open_detention_logs():
    """Displays a fake detention log text file with humorous incident reports."""
    win = StyledWindow(root, "Detention_Logs.txt — Notepad", 696, 600)

    # Notepad-style toolbar
    menubar = tk.Frame(win.content, bg='#f0f0f0', relief=tk.FLAT)
    menubar.pack(fill=tk.X)
    for lbl in ["File", "Edit", "Format", "View", "Help"]:
        tk.Label(menubar, text=lbl, font=('Tahoma', 15), fg='#000000',
                 bg='#f0f0f0', padx=6, pady=2).pack(side=tk.LEFT)

    tk.Frame(win.content, bg='#c0c0c0', height=1).pack(fill=tk.X)

    # Text area
    txt_frame = tk.Frame(win.content, bg='white')
    txt_frame.pack(fill=tk.BOTH, expand=True)

    txt = tk.Text(txt_frame, font=('Courier New', 15), bg='white', fg='#000000',
                  relief=tk.FLAT, bd=0, wrap=tk.WORD,
                  padx=8, pady=6, state=tk.NORMAL)
    vsb3 = tk.Scrollbar(txt_frame, orient='vertical', command=txt.yview)
    txt.configure(yscrollcommand=vsb3.set)
    vsb3.pack(side=tk.RIGHT, fill=tk.Y)
    txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    log_content = """\
LEGS ACADEMY — DETENTION LOG
Academic Year: 2024-25
Maintained by: Vice Principal Henderson (and his very tired pen)
============================================================

DATE:       Mon, Sep 09, 2024 — 3:15 PM
STUDENT:    Tyler Pranksworth, Grade 7
TEACHER:    Mrs. Flannery (History)
OFFENSE:    Drew a moustache on every single face in the history textbook, including the maps. Magellan now has a goatee.
PUNISHMENT: 1 hour. Must write "I will not redecorate historical figures" 100 times. Tried to write it in calligraphy. Points for style, zero for judgment.
------------------------------------------------------------

DATE:       Wed, Sep 18, 2024 — 3:15 PM
STUDENT:    Cody McSneeze, Grade 6
TEACHER:    Mr. Plunkett (Science)
OFFENSE:    Claimed his cold was "a science experiment in airborne particle distribution." Distributed particles over three rows of students.
PUNISHMENT: 45 min + must bring tissues tomorrow. Brought 47 boxes. We're covered for winter.
------------------------------------------------------------

DATE:       Fri, Oct 04, 2024 — 3:15 PM
STUDENT:    Emma Giggleston, Grade 8
TEACHER:    Ms. Pringle (English)
OFFENSE:    Rewrote the weekly vocabulary quiz as a rap song and performed it. Got every answer correct. Still in detention. (Ms. Pringle is still humming it. Do not tell Emma.)
PUNISHMENT: 1 hour. Used the time to write a second rap. Principal rated it 8/10. This stays off the record. Except it is on the record.
------------------------------------------------------------

DATE:       Tue, Oct 22, 2024 — 3:15 PM
STUDENT:    Jake Kim, Grade 7
TEACHER:    Coach Bellamy (P.E.)
OFFENSE:    Convinced the class that "competitive sitting" was an Olympic sport and held trials. 28 students participated. 2 fell asleep. Coach Bellamy nearly joined them.
PUNISHMENT: 1 hour. Sat very still. Irony noted by all.
------------------------------------------------------------

DATE:       Thu, Nov 07, 2024 — 3:15 PM
STUDENT:    Sophie Bananapeels, Grade 6
TEACHER:    Mr. Fitch (Math)
OFFENSE:    Replaced all the 7s on the classroom number line with drawings of a chicken. 7 is now a chicken. Students cannot unlearn this. Three kids now say "chicken" instead of 7 on tests.
PUNISHMENT: 1 hour. Must make new number line. Made one with better chickens. It was confiscated. Then laminated. It's in the teacher's lounge now.
------------------------------------------------------------

DATE:       Mon, Dec 02, 2024 — 3:15 PM
STUDENT:    Benny Noodlestir, Grade 7
TEACHER:    Mrs. Flannery (History)
OFFENSE:    During silent reading, communicated entirely using hand puppets made from his socks. Conducted a full interview with 'Señor Left Sock' regarding the fall of the Roman Empire. Actually pretty historically accurate.
PUNISHMENT: 1 hour. Señor Left Sock was confiscated pending review.
------------------------------------------------------------

DATE:       Wed, Jan 15, 2025 — 3:15 PM
STUDENT:    Tyler Pranksworth, Grade 7
TEACHER:    Multiple (class-wide incident)
OFFENSE:    Organised what he called a "Flash Freeze" — at exactly 10:00 AM every student stopped moving simultaneously for 60 seconds. Four teachers checked for a gas leak. Fire dept was not called. (It was a close call.)
PUNISHMENT: 2 hours. Tyler sat completely still in detention as a "personal record attempt." Made it 3 minutes. New record.
------------------------------------------------------------

DATE:       Fri, Feb 14, 2025 — 3:15 PM
STUDENT:    Lily Butterfingers, Grade 6
TEACHER:    Ms. Pringle (English)
OFFENSE:    Valentine's Day. Lily made 32 valentines. Each one individually glittered. The glitter is still in the HVAC system. Maintenance says it will shimmer until roughly 2031.
PUNISHMENT: 1 hour. Spent 58 minutes apologising. 2 minutes crying. Glitter everywhere regardless.
------------------------------------------------------------

DATE:       Tue, Mar 11, 2025 — 3:15 PM
STUDENT:    Marcus Loudmouth, Grade 8
TEACHER:    Mr. Plunkett (Science)
OFFENSE:    Tested acoustic properties of cafeteria by yelling "ECHO!" repeatedly until the jello on 14 trays achieved visible resonance. Considered noteworthy by Physics dept. Still detention.
PUNISHMENT: 1 hour. Was very quiet. Suspiciously quiet.
------------------------------------------------------------

NOTE FROM V.P. HENDERSON:
If Tyler Pranksworth appears in this log one more time, we are giving him his own column. Possibly his own ZIP code.

Also: whoever replaced the staff room sugar with salt AGAIN, we know it was not Tyler this time. The forensic evidence points to 6th grade. You know who you are. The coffee knows who you are.

============================================================
END OF LOG — Page 1 of 1
Printed: 2025-05-22   [CONFIDENTIAL — Staff Use Only]
"""
    txt.insert(tk.END, log_content)
    txt.config(state=tk.DISABLED)

    status = tk.Label(win.content,
                      text="Ln 1, Col 1    UTF-8    Windows (CRLF)",
                      font=('Tahoma', 14), bg='#f0f0f0', fg='#444444',
                      anchor='w', relief=tk.SUNKEN, bd=1)
    status.pack(fill=tk.X, side=tk.BOTTOM)

# ─── Grade Portal ─────────────────────────────────────────────────────────────
def open_grade_portal():
    """Creates the secure login gate for the grade portal."""
    win = StyledWindow(root, "Secure Database Gateway", 430, 270)
    tk.Label(win.content, text="🔒  ENCRYPTED PORTAL",
             font=('Tahoma', 14, 'bold'), fg='#a01818',
             bg=win.WIN_BG).pack(pady=(18, 4))
    tk.Label(win.content, text="Enter Database Encryption Key:",
             font=('Tahoma', 10), bg=win.WIN_BG, fg='#111111').pack()
    entry = tk.Entry(win.content, font=('Tahoma', 12), show="●",
                     justify="center", relief=tk.FLAT, bd=0,
                     bg='white', fg='#000000', width=22,
                     insertbackground='#1c5aaa',
                     insertontime=600, insertofftime=300,
                     highlightthickness=2,
                     highlightbackground='#4a88d8',
                     highlightcolor='#6ab0ff')
    entry.pack(pady=8)

    err_lbl = tk.Label(win.content, text="", font=('Tahoma', 13, 'bold'),
                       fg='#a01818', bg=win.WIN_BG)
    err_lbl.pack(pady=(0, 4))

    win.after(50, entry.focus_set)

    def verify():
        global portal_attempts
        if entry.get().strip().lower() == PORTAL_PASSWORD:
            win.destroy()
            show_grade_modifier_interface()
        else:
            portal_attempts += 1
            if portal_attempts >= 4:
                win.destroy()
                trigger_lose_condition()
            else:
                rem = 4 - portal_attempts
                err_lbl.config(text=f"⚠️  Access Denied! Attempt {portal_attempts}/3 (Lockout in {rem}...)")
                entry.delete(0, tk.END)
                entry.focus_set()

    win.bind('<Return>', lambda e: verify())
    btn = os_button(win.content, "  Authenticate  ", verify,
                    font=('Tahoma', 10, 'bold'))
    btn.pack(pady=6)


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
        tk.Label(row, text=f"{subject}:", font=('Tahoma', 12, 'bold'),
                 fg='#1a1a1a', bg=win.WIN_BG, width=12, anchor='e').pack(side=tk.LEFT, padx=6)
        var = tk.StringVar(value="F")
        opt = tk.OptionMenu(row, var, "A", "B", "C", "D", "F")
        opt.config(font=('Tahoma', 11), width=4,
                   bg='#d8d4c6', fg='#111111', activeforeground='#000000',
                   relief=tk.RAISED, bd=2)
        opt.pack(side=tk.LEFT)
        dropdowns[subject] = var

    tk.Frame(win.content, bg='#b8a888', height=1).pack(fill=tk.X, padx=15, pady=8)

    status_lbl = tk.Label(win.content, text="", font=('Tahoma', 14, 'bold'),
                          fg='#a01818', bg=win.WIN_BG)
    status_lbl.pack(pady=4)

    def submit_grades():
        if all(dropdowns[s].get() == "A" for s in student_grades):
            status_lbl.config(text="🔄  Syncing with database... Please wait.", fg='#246e28')
            btn.unbind('<Button-1>')
            def success_trigger():
                win.destroy()
                trigger_win_condition()
            win.after(1200, success_trigger)
        else:
            status_lbl.config(text="⚠️  Sync Failed: Student GPA remains below passing threshold.", fg='#a01818')

    btn = os_button(win.content, "  Commit Changes to Server  ", submit_grades,
                    font=('Tahoma', 11, 'bold'),
                    bg='#246e28',
                    activebackground='#2e8832',
                    highlightbackground='#185020')
    btn.pack(pady=4)

# ─── Win Condition ────────────────────────────────────────────────────────────
class MatrixRain:
    def __init__(self, canvas, width, height, theme='green'):
        self.c = canvas
        self.w = width
        self.h = height
        self.theme = theme

        # Grid columns: each spaced by 18 pixels
        self.cols = width // 18
        self.drops = [random.randint(-40, 0) * 15 for _ in range(self.cols)]
        self.speeds = [random.randint(12, 28) for _ in range(self.cols)]
        self.chars = []

    def update(self):
        new_chars = []
        for cid, col, age in self.chars:
            age += 1
            if age > 14:
                self.c.delete(cid)
            else:
                # Fading gradient according to theme
                if age < 2:
                    color = '#ffffff'
                elif age < 5:
                    color = '#ff2020' if self.theme == 'red' else '#00ff41'
                elif age < 9:
                    color = '#aa1010' if self.theme == 'red' else '#00aa30'
                else:
                    color = '#350000' if self.theme == 'red' else '#002500'
                self.c.itemconfig(cid, fill=color)
                new_chars.append((cid, col, age))
        self.chars = new_chars

        for i in range(self.cols):
            self.drops[i] += self.speeds[i]
            if self.drops[i] > self.h + 50:
                self.drops[i] = random.randint(-15, 0) * 15
                self.speeds[i] = random.randint(12, 28)

            if self.drops[i] > 0 and random.random() > 0.15:
                cx = i * 18 + 9
                cy = self.drops[i]
                char = random.choice('010101ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*')
                cid = self.c.create_text(cx, cy, text=char, fill='#ffffff',
                                         font=('Courier New', 11, 'bold'))
                self.chars.append((cid, i, 0))

        # Keep winning/losing text elements raised above the digital rain
        self.c.tag_raise('win_text')
        self.c.after(45, self.update)


def play_win_fanfare():
    """Synthesizes a retro 8-bit winning arpeggio and plays it asynchronously."""
    import math as _math
    import struct as _struct
    import wave as _wave
    import subprocess as _subprocess
    import sys as _sys

    notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6 arpeggio
    durations = [0.15, 0.15, 0.15, 0.50]
    sample_rate = 8000
    audio_data = bytearray()

    for freq, dur in zip(notes, durations):
        num_samples = int(sample_rate * dur)
        for i in range(num_samples):
            # Square wave for authentic retro 8-bit chip-tune sound
            t = i / sample_rate
            cycle = t * freq
            val = 127 if (cycle - _math.floor(cycle)) < 0.5 else -128
            audio_data.append(val + 128)

    wav_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "win.wav")
    try:
        with _wave.open(wav_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(1)
            w.setframerate(sample_rate)
            w.writeframes(audio_data)

        if _sys.platform == "darwin":
            _subprocess.Popen(["afplay", wav_path], stdout=_subprocess.DEVNULL, stderr=_subprocess.DEVNULL)
        elif _sys.platform == "win32":
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            _subprocess.Popen(["aplay", wav_path], stdout=_subprocess.DEVNULL, stderr=_subprocess.DEVNULL)
    except Exception as _err:
        print(f"[AUDIO] Could not play fanfare: {_err}")


def play_lose_sound():
    """Synthesizes a retro 8-bit hazard alarm siren and plays it asynchronously."""
    import math as _math
    import struct as _struct
    import wave as _wave
    import subprocess as _subprocess
    import sys as _sys

    notes = [220, 180, 220, 180, 220, 180, 150]  # Hazard siren pitches
    durations = [0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.6]
    sample_rate = 8000
    audio_data = bytearray()

    for freq, dur in zip(notes, durations):
        num_samples = int(sample_rate * dur)
        for i in range(num_samples):
            t = i / sample_rate
            cycle = t * freq
            # Square wave for a dirty hazard buzzer sound
            val = 127 if (cycle - _math.floor(cycle)) < 0.5 else -128
            audio_data.append(val + 128)

    wav_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "lose.wav")
    try:
        with _wave.open(wav_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(1)
            w.setframerate(sample_rate)
            w.writeframes(audio_data)

        if _sys.platform == "darwin":
            _subprocess.Popen(["afplay", wav_path], stdout=_subprocess.DEVNULL, stderr=_subprocess.DEVNULL)
        elif _sys.platform == "win32":
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            _subprocess.Popen(["aplay", wav_path], stdout=_subprocess.DEVNULL, stderr=_subprocess.DEVNULL)
    except Exception as _err:
        print(f"[AUDIO] Could not play lose alarm: {_err}")


def trigger_win_condition():
    """Unlocks the door, plays win fanfare, and runs animated Matrix digital rain."""
    for w in root.winfo_children():
        w.destroy()
    root.configure(bg='#000000')
    SW = root.winfo_screenwidth()
    SH = root.winfo_screenheight()
    c = tk.Canvas(root, bg='#000000', highlightthickness=0)
    c.pack(fill=tk.BOTH, expand=True)

    # Animated Matrix rain screensaver (green theme)
    rain = MatrixRain(c, SW, SH, theme='green')
    rain.update()

    # SYSTEM OVERRIDE HUD (always layered on top of rain with tag 'win_text')
    shadow_text(c, SW//2, SH//2-60, text="SYSTEM OVERRIDE",
                font=('Courier New', 46, 'bold'), fill='#00ff41', tags='win_text')
    shadow_text(c, SW//2, SH//2+20, text="EXIT DOOR UNLOCKED",
                font=('Courier New', 32, 'bold'), fill='#00cc33', tags='win_text')

    door_lock.on()
    root.unbind('<Return>')
    root.focus_force()

    # Play retro 8-bit arpeggio fanfare asynchronously
    play_win_fanfare()


def trigger_lose_condition():
    """Triggers the security breach lockdown screen with red Matrix rain."""
    for w in root.winfo_children():
        w.destroy()
    root.configure(bg='#0a0000')
    SW = root.winfo_screenwidth()
    SH = root.winfo_screenheight()
    c = tk.Canvas(root, bg='#0a0000', highlightthickness=0)
    c.pack(fill=tk.BOTH, expand=True)

    # Red Matrix digital rain screensaver
    rain = MatrixRain(c, SW, SH, theme='red')
    rain.update()

    # SECURITY LOCKDOWN HUD (always layered on top of rain with tag 'win_text')
    shadow_text(c, SW//2, SH//2-60, text="SECURITY BREACH DETECTED",
                font=('Courier New', 42, 'bold'), fill='#ff2020', tags='win_text')
    shadow_text(c, SW//2, SH//2+20, text="SYSTEM PERMANENTLY LOCKED",
                font=('Courier New', 28, 'bold'), fill='#dddddd', tags='win_text')
    shadow_text(c, SW//2, SH//2+80, text="District Security has been notified.",
                font=('Courier New', 16, 'italic'), fill='#aa9999', tags='win_text')

    root.unbind('<Return>')
    root.focus_force()

    # Play retro 8-bit hazard alarm sound
    play_lose_sound()

# ─── Desktop Cloud Helper ─────────────────────────────────────────────────────
import math as _math

def _catmull_points(pts, steps=12):
    """Expand a list of (x,y) control points into a smooth Catmull-Rom curve."""
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[max(i-1, 0)]
        p1 = pts[i]
        p2 = pts[i+1]
        p3 = pts[min(i+2, n-1)]
        for t in range(steps):
            tt = t / steps
            tt2 = tt*tt; tt3 = tt2*tt
            x = 0.5*((2*p1[0])
                     + (-p0[0]+p2[0])*tt
                     + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*tt2
                     + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*tt3)
            y = 0.5*((2*p1[1])
                     + (-p0[1]+p2[1])*tt
                     + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*tt2
                     + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*tt3)
            out.extend([x, y])
    out.extend(pts[-1])
    return out

def draw_cloud(c, cx, cy, sz):
    """Volumetric XP-style cumulus cloud: shadow base → grey mid → white tops."""
    # Shadow ellipse on sky
    c.create_oval(cx - sz, cy + sz//3,
                  cx + sz, cy + sz//3 + sz//3,
                  fill='#b8d8ec', outline='')
    # Puff definitions: (dx, dy, rx, ry, colour)
    puffs = [
        # grey underlayer
        ( 0,      sz//5,   sz,      sz*2//5, '#d8e8f4'),
        (-sz//2,  sz//4,   sz*3//5, sz*3//8, '#ddeaf6'),
        ( sz//2,  sz//4,   sz*3//5, sz*3//8, '#ddeaf6'),
        # bright mid
        (-sz//3,  0,       sz*3//5, sz//2,   '#eef4fb'),
        ( sz//3,  0,       sz*3//5, sz//2,   '#eef4fb'),
        ( 0,     -sz//6,   sz*2//3, sz//2,   '#f4f8fd'),
        # bright tops
        (-sz//4, -sz//3,   sz//2,   sz//3,   '#ffffff'),
        ( sz//4, -sz//3,   sz//2,   sz//3,   '#ffffff'),
        ( 0,     -sz//2,   sz*2//5, sz//3,   '#ffffff'),
        # highlight peak
        ( 0,     -sz*2//3, sz//4,   sz//5,   '#ffffff'),
    ]
    for dx, dy, rx, ry, col in puffs:
        c.create_oval(cx+dx-rx, cy+dy-ry, cx+dx+rx, cy+dy+ry,
                      fill=col, outline='')

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
                       fill='white', font=('Tahoma', 14, 'bold'))

    draw_start()
    sb.bind('<Enter>', lambda e: draw_start(True))
    sb.bind('<Leave>', lambda e: draw_start(False))
    tb.create_window(6, TBAR_H//2, window=sb, anchor='w')

    # System tray clock
    clk = tk.Label(tb, font=('Tahoma', 13), bg='#c0c0c0',
                   fg='#000000', relief=tk.SUNKEN, bd=1, padx=4)
    tb.create_window(SW - 6, TBAR_H//2, window=clk, anchor='e')
    update_clock(clk)

    # ── Wallpaper Canvas ───────────────────────────────────────────────────────
    wc = tk.Canvas(root, highlightthickness=0, bg='#1a1a1a')
    wc.pack(fill=tk.BOTH, expand=True)

    # ── LEGS Academy photo as full desktop wallpaper ───────────────────────────
    _script_dir = _os.path.dirname(_os.path.abspath(__file__))
    _img_path   = _os.path.join(_script_dir, 'legs_academy.png')
    _wp_photo   = None
    if _PIL_OK and _os.path.exists(_img_path):
        from PIL import ImageEnhance as _IE, ImageDraw as _ID
        _pil = _PILImage.open(_img_path).convert('RGB')
        # Scale to cover the full desktop area
        src_w, src_h = _pil.size
        scale = max(SW / src_w, DH / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        _pil  = _pil.resize((new_w, new_h), _PILImage.LANCZOS)
        # Centre-crop to exact desktop size
        left = (new_w - SW) // 2
        top  = (new_h - DH) // 2
        _pil = _pil.crop((left, top, left + SW, top + DH))

        # ── Bake vignette/contrast into PIL (tkinter stipple ≠ alpha blend) ──
        # Slight overall darkening so desktop feels like a proper OS wallpaper
        _pil = _IE.Brightness(_pil).enhance(0.78)

        # Dark left strip so icons always have contrast
        _overlay = _PILImage.new('RGB', (SW, DH), (0, 0, 0))
        _mask    = _PILImage.new('L',   (SW, DH), 0)
        _draw    = _ID.Draw(_mask)
        # Left gradient strip (icon column)
        for _x in range(140):
            _alpha = int(160 * (1 - _x / 140))
            _draw.line([(_x, 0), (_x, DH)], fill=_alpha)
        # Bottom strip
        for _y in range(int(DH * 0.82), DH):
            _t     = (_y - int(DH * 0.82)) / max(DH - int(DH * 0.82), 1)
            _alpha = int(120 * _t)
            _draw.line([(0, _y), (SW, _y)], fill=_alpha)
        _pil = _PILImage.composite(_overlay, _pil, _mask)

        _wp_photo    = _PILImageTk.PhotoImage(_pil)
        wc._wp_photo = _wp_photo        # keep reference — prevents GC
        wc.create_image(0, 0, image=_wp_photo, anchor='nw')
    else:
        # Fallback gradient if image missing
        fill_gradient(wc, 0, 0, SW, DH, '#1a3060', '#0a1828', steps=120)

    # ── OS watermark ──────────────────────────────────────────────────────────
    shadow_text(wc, SW-18, 15, text="EduOS Professional",
                font=('Tahoma', 17, 'italic'), fill='white', anchor='ne')

    # ── Desktop Icons — dark backdrop pill for guaranteed contrast ─────────────
    # horizon_y / haze_y are not defined in photo mode; set dummies so
    # the icon loop below still works without them.
    horizon_y = int(DH * 0.60)
    haze_y    = int(DH * 0.65)

    # ── Desktop Icons — dark pill backdrop guarantees contrast ────────────────
    ICON_X      = 52          # horizontal centre of icon column
    ICON_BTN_W  = 70
    ICON_BTN_H  = 52
    ICON_LBL_W  = 86
    ICON_SPACING= 102

    icon_defs = [
        ("📁", "School\nBudget.xlsx",  open_school_budget),
        ("📄", "Suspension\nList.pdf", open_suspension_list),
        ("📝", "Detention\nLogs.txt",  open_detention_logs),
        ("🌐", "Grade\nPortal",        open_grade_portal),
    ]

    PILL_BG   = '#181818'   # near-black icon button bg
    PILL_HOV  = '#2a3a6a'   # hover: dark navy blue
    PILL_FG   = '#ffffff'   # white label text

    for i, (ico, name, cmd) in enumerate(icon_defs):
        iy = 18 + i * ICON_SPACING

        # Dark pill shadow behind the whole icon cell (icon + label)
        cell_top    = iy - 6
        cell_bottom = iy + ICON_BTN_H + 28
        cell_left   = ICON_X - ICON_LBL_W // 2 - 4
        cell_right  = ICON_X + ICON_LBL_W // 2 + 4
        # Outer dark shadow
        wc.create_rectangle(cell_left + 3, cell_top + 3,
                             cell_right + 3, cell_bottom + 3,
                             fill='#000000', outline='', stipple='gray50')
        # Pill body — solid dark panel
        wc.create_rectangle(cell_left, cell_top,
                             cell_right, cell_bottom,
                             fill=PILL_BG, outline='#404040', width=1)
        # Subtle top-shine line
        wc.create_line(cell_left+2, cell_top+1,
                       cell_right-2, cell_top+1,
                       fill='#555555', width=1)

        # Icon button (transparent-looking against dark pill)
        ib = tk.Button(wc, text=ico, font=('Helvetica', 30),
                       bg=PILL_BG, fg=PILL_FG,
                       relief=tk.FLAT, bd=0,
                       activebackground=PILL_HOV,
                       activeforeground=PILL_FG,
                       cursor='hand2', command=cmd)
        wc.create_window(ICON_X, iy + ICON_BTN_H // 2,
                         window=ib, width=ICON_BTN_W, height=ICON_BTN_H)
        ib.bind('<Enter>', lambda e, b=ib: b.config(bg=PILL_HOV))
        ib.bind('<Leave>', lambda e, b=ib: b.config(bg=PILL_BG))

        # Label — white text on transparent (pill bg shows through)
        nl = tk.Label(wc, text=name, font=('Tahoma', 12),
                      bg=PILL_BG, fg=PILL_FG,
                      justify=tk.CENTER, relief=tk.FLAT, bd=0)
        wc.create_window(ICON_X, iy + ICON_BTN_H + 14,
                         window=nl, width=ICON_LBL_W)
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
                           bg='#d0e4f8', fg='#000000',
                           insertbackground='#1c5aaa',
                           insertontime=600, insertofftime=300,
                           width=18,
                           highlightthickness=2,
                           highlightbackground='#3a78c0',
                           highlightcolor='#58aaff')
bg.create_window(SW//2, py+170, window=comp_pass_entry,
                 width=222, height=30)
root.after(100, comp_pass_entry.focus_set)

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

login_error_text = bg.create_text(SW//2, py+285, text="",
                                  font=('Tahoma', 14, 'bold'), fill='#ff8888')

# ── Bottom status bar ─────────────────────────────────────────────────────────
fill_gradient(bg, 0, SH-48, SW, SH, '#010818', '#040e24', steps=48)
bg.create_line(0, SH-48, SW, SH-48, fill='#163054', width=1)
shadow_text(bg, SW//2, SH-24,
            text="Press Ctrl+Alt+Del to unlock  •  EduOS Professional Edition",
            font=('Tahoma', 9), fill='#4070a8')

# ─── Key Bindings ─────────────────────────────────────────────────────────────
root.bind('<Return>',                lambda e: check_computer_login())
root.bind_all('<Control-Option-Escape>',     gm_backdoor_trigger)
root.bind_all('<Control-Alt-Escape>',        gm_backdoor_trigger)
root.bind_all('<Control-Option-r>',          gm_reset_trigger)
root.bind_all('<Control-Option-R>',          gm_reset_trigger)
root.bind_all('<Control-Alt-r>',             gm_reset_trigger)
root.bind_all('<Control-Alt-R>',             gm_reset_trigger)
root.bind_all('<Control-Option-registered>', gm_reset_trigger)
root.bind_all('<Control-Alt-registered>',    gm_reset_trigger)
root.bind_all('<Control-Option-permille>',   gm_reset_trigger)
root.bind_all('<Control-Alt-permille>',      gm_reset_trigger)

root.mainloop()
