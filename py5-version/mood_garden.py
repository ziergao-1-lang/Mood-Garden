# -*- coding: utf-8 -*-
# Mood Garden (py5 build)
#
# Same window and same behaviour as the one in processing-python/, running on py5 instead,
# so PyCharm can open it with a plain Run.
# Typing Chinese is the one real difference: Processing never sees the IME, so that build
# falls back to a dialog. Here keystrokes arrive normally.

import json
import threading
from datetime import date, timedelta
from pathlib import Path

import py5

W = 900
H = 720

MOODS = ["Happy", "Calm", "Sad", "Anxious", "Energetic"]
MOOD_COLORS = [
    (244, 182, 76),
    (91, 166, 145),
    (104, 142, 184),
    (166, 126, 190),
    (231, 112, 91)
]
WEATHERS = ["Sunny", "Cloudy", "Rainy", "Windy"]

NOTE_LIMIT = 80
# 20px lines starting 22px below the top edge. 80 CJK characters wrap to three lines at most,
# so the last baseline lands at 551 with 9px to spare above the bottom edge at 560.
LINE_H = 20
NOTE_TEXT_TOP = 22

# Note box and save button live here because both draw() and the click handler need them.
# They used to be spelled out in two places, which is how a layout change gets half applied.
NOTE_X, NOTE_Y, NOTE_W, NOTE_H = 52, 489, 466, 71
SAVE_X, SAVE_Y, SAVE_W, SAVE_H = 52, 576, 153, 34

# Data sits next to this file, not wherever the process happens to be started from.
# PyCharm usually runs with the project root as cwd, so a relative path writes somewhere else.
DATA_FILE = Path(__file__).resolve().parent / "mood_entries.json"

entries = []
mood_pick = 0
weather_pick = 0
note = ""
typing = False
status = ""
last_click_at = 0
dialog_open = False

# Wrapping is cached. As long as note is unchanged there is no reason to measure text_width
# again, and doing it for every character on every frame costs real frames.
wrapped_lines = []
wrapped_for = None


def settings():
    # py5 insists size and smooth happen here. In setup() they throw.
    py5.size(W, H)
    py5.smooth(4)


def setup():
    py5.window_title("Mood Garden")
    py5.text_font(pick_font())
    load_entries()
    restore_today()


def draw():
    draw_background()
    draw_header()
    draw_form()
    draw_moods()
    draw_weather()
    draw_note_box()
    draw_save_row()
    draw_week_card()
    draw_recent_card()
    draw_footer()


def pick_font():
    # The UI is English, but people will type Chinese into it, so ask for a font with those
    # glyphs rather than getting a row of boxes.
    # py5 has no PFont.list(), so try candidates in order and keep the first one that builds.
    for want in ["Microsoft YaHei", "PingFang SC", "Hiragino Sans GB",
                 "Noto Sans CJK SC", "Source Han Sans CN",
                 "WenQuanYi Micro Hei", "SimHei", "SansSerif"]:
        try:
            return py5.create_font(want, 15)
        except Exception:
            continue
    return py5.create_font("SansSerif", 15)



def draw_background():
    py5.background(247, 246, 239)
    py5.no_stroke()
    py5.fill(228, 240, 230)
    py5.ellipse(850, 20, 220, 180)
    py5.fill(239, 228, 207)
    py5.ellipse(35, 680, 180, 150)


def draw_header():
    py5.fill(42, 66, 62)
    py5.text_size(30)
    py5.text_align(py5.LEFT, py5.BASELINE)
    py5.text("Mood Garden", 36, 52)

    py5.fill(110, 128, 119)
    py5.text_size(14)
    py5.text("One line a day. No streaks to keep.", 38, 77)

    draw_sun(809, 49, 19)
    draw_cloud(843, 65, 0.72)


def draw_form():
    card(30, 105, 510, 515)

    py5.fill(42, 66, 62)
    py5.text_size(18)
    py5.text_align(py5.LEFT, py5.BASELINE)
    py5.text("Today's check-in", 52, 139)

    py5.fill(120, 137, 128)
    py5.text_size(12)
    py5.text(date.today().strftime("%a, %d %b %Y").upper(), 52, 161)


def draw_moods():
    py5.fill(55, 76, 69)
    py5.text_size(14)
    py5.text_align(py5.LEFT, py5.BASELINE)
    py5.text("Pick the mood that's closest", 52, 197)

    for i in range(len(MOODS)):
        x = 52 + (i % 3) * 151
        y = 214 + (i // 3) * 62
        picked = (i == mood_pick)
        hovered = over_rect(x, y, 137, 49)

        if picked:
            py5.fill(232, 243, 235)
            py5.stroke(MOOD_COLORS[i][0], MOOD_COLORS[i][1], MOOD_COLORS[i][2])
        elif hovered:
            py5.fill(250, 249, 244)
            py5.stroke(190, 207, 195)
        else:
            py5.fill(255, 254, 250)
            py5.stroke(230, 229, 220)
        py5.stroke_weight(1.2)
        py5.rect(x, y, 137, 49, 12)
        py5.no_stroke()

        draw_mood_icon(i, x + 25, y + 24)

        py5.fill(54, 72, 66)
        py5.text_size(13)
        py5.text_align(py5.LEFT, py5.CENTER)
        py5.text(MOODS[i], x + 45, y + 25)

    py5.text_align(py5.LEFT, py5.BASELINE)


def draw_weather():
    py5.fill(55, 76, 69)
    py5.text_size(14)
    py5.text_align(py5.LEFT, py5.BASELINE)
    py5.text("And the weather?", 52, 365)

    for i in range(len(WEATHERS)):
        x = 52 + i * 113
        y = 381
        if i == weather_pick:
            py5.fill(232, 243, 235)
            py5.stroke(103, 164, 142)
        else:
            py5.fill(255, 254, 250)
            py5.stroke(230, 229, 220)
        py5.stroke_weight(1)
        py5.rect(x, y, 101, 67, 12)
        py5.no_stroke()

        draw_weather_icon(i, x + 50, y + 23)

        py5.fill(74, 94, 85)
        py5.text_size(11)
        py5.text_align(py5.CENTER, py5.CENTER)
        py5.text(WEATHERS[i], x + 50, y + 52)

    py5.text_align(py5.LEFT, py5.BASELINE)


def draw_note_box():
    py5.fill(55, 76, 69)
    py5.text_size(14)
    py5.text_align(py5.LEFT, py5.BASELINE)
    py5.text("A note to yourself", NOTE_X, 475)

    # Counter sits on the title row instead of inside the box, where it would fight the text.
    py5.fill(150, 160, 151)
    py5.text_size(10)
    py5.text_align(py5.RIGHT, py5.BASELINE)
    py5.text(str(len(note)) + " / " + str(NOTE_LIMIT), NOTE_X + NOTE_W, 475)
    py5.text_align(py5.LEFT, py5.BASELINE)

    if typing:
        py5.fill(255, 255, 252)
        py5.stroke(93, 164, 142)
        py5.stroke_weight(1.5)
    else:
        py5.fill(255, 254, 250)
        py5.stroke(230, 229, 220)
        py5.stroke_weight(1)
    py5.rect(NOTE_X, NOTE_Y, NOTE_W, NOTE_H, 11)
    py5.no_stroke()

    if note == "":
        py5.fill(160, 169, 160)
        py5.text_size(12)
        py5.text("Click here and type. Double-click to write more.",
                 NOTE_X + 14, NOTE_Y + 26)
        return

    # Set the body size before wrapping. note_lines() measures with text_width, and if it runs
    # while the size is still 10 from the counter above, it thinks more fits per line than does.
    # The result is text drawn at 13 that runs straight out of the box.
    py5.fill(65, 82, 73)
    py5.text_size(13)
    lines = note_lines()
    for i in range(len(lines)):
        py5.text(lines[i], NOTE_X + 14, NOTE_Y + NOTE_TEXT_TOP + i * LINE_H)

    # Blinking caret, otherwise there is no sign the box is taking input.
    if typing and (py5.millis() // 500) % 2 == 0:
        last = lines[len(lines) - 1]
        cx = NOTE_X + 14 + py5.text_width(last) + 1
        cy = NOTE_Y + NOTE_TEXT_TOP + (len(lines) - 1) * LINE_H
        py5.stroke(93, 164, 142)
        py5.stroke_weight(1.5)
        py5.line(cx, cy - 11, cx, cy + 3)
        py5.no_stroke()


def draw_save_row():
    hovered = over_rect(SAVE_X, SAVE_Y, SAVE_W, SAVE_H)
    py5.no_stroke()
    if hovered:
        py5.fill(46, 112, 94)
    else:
        py5.fill(62, 131, 111)
    py5.rect(SAVE_X, SAVE_Y, SAVE_W, SAVE_H, 10)

    py5.fill(255, 255, 255)
    py5.text_size(12)
    py5.text_align(py5.CENTER, py5.CENTER)
    py5.text("Save today's mood", SAVE_X + SAVE_W / 2, SAVE_Y + SAVE_H / 2)

    if status != "":
        py5.fill(104, 130, 118)
        py5.text_size(11)
        py5.text_align(py5.LEFT, py5.CENTER)
        py5.text(status, SAVE_X + SAVE_W + 14, SAVE_Y + SAVE_H / 2)

    py5.text_align(py5.LEFT, py5.BASELINE)


def draw_week_card():
    card(560, 105, 310, 242)

    py5.fill(42, 66, 62)
    py5.text_size(17)
    py5.text_align(py5.LEFT, py5.BASELINE)
    py5.text("Mood by day", 582, 139)

    py5.fill(116, 135, 126)
    py5.text_size(11)
    py5.text("Last 7 days", 582, 159)

    chart_x = 590
    chart_y = 190
    chart_h = 112
    chart_w = 252

    py5.stroke(229, 231, 222)
    py5.stroke_weight(1)
    py5.line(chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h)
    py5.no_stroke()

    for offset in range(6, -1, -1):
        day = date.today() - timedelta(days=offset)
        i = 6 - offset
        found = find_entry(day.isoformat())

        x = chart_x + 9 + i * 35

        if found is None:
            py5.fill(228, 230, 222)
            py5.rect(x, chart_y + chart_h - 8, 22, 8, 5)
        else:
            idx = mood_index_for(found.get("mood", ""))
            if idx < 0:
                py5.fill(200, 200, 195)
            else:
                c = MOOD_COLORS[idx]
                py5.fill(c[0], c[1], c[2])
            # Fixed height. A bar means the day got a page, nothing about how strong the mood was.
            py5.rect(x, chart_y + chart_h - 48, 22, 48, 6)
            py5.ellipse(x + 11, chart_y + chart_h - 53, 10, 10)

        py5.fill(119, 135, 124)
        py5.text_size(9)
        py5.text_align(py5.CENTER, py5.CENTER)
        py5.text(day.strftime("%a")[:1], x + 11, chart_y + chart_h + 16)

    py5.text_align(py5.LEFT, py5.BASELINE)
    py5.fill(119, 135, 124)
    py5.text_size(10)
    # This caption used to sit at 333, two pixels under the weekday letters, and read as
    # one smudged line. Moved down to 339.
    py5.text("A bar just means a page got written that day.", 582, 339)


def draw_recent_card():
    card(560, 365, 310, 255)

    py5.fill(42, 66, 62)
    py5.text_size(17)
    py5.text_align(py5.LEFT, py5.BASELINE)
    py5.text("Recent pages", 582, 399)

    if len(entries) == 0:
        draw_leaf(608, 470, 1.0)
        py5.fill(119, 135, 124)
        py5.text_size(12)
        py5.text("Nothing saved yet.", 632, 465)
        py5.text("Today's check-in is on the left.", 632, 486)
        return

    y = 431
    for entry in entries[-5:][::-1]:
        idx = mood_index_for(entry.get("mood", ""))
        if idx < 0:
            py5.fill(200, 200, 195)
        else:
            c = MOOD_COLORS[idx]
            py5.fill(c[0], c[1], c[2])
        py5.ellipse(590, y - 4, 10, 10)

        py5.fill(57, 77, 68)
        py5.text_size(12)
        py5.text_align(py5.LEFT, py5.BASELINE)
        py5.text(as_text(entry.get("mood", "?")), 605, y)

        py5.fill(137, 151, 141)
        py5.text_size(10)
        py5.text_align(py5.RIGHT, py5.BASELINE)
        py5.text(as_text(entry.get("date", "")), 848, y)
        py5.text_align(py5.LEFT, py5.BASELINE)

        py5.fill(110, 127, 118)
        py5.text_size(10)
        meta = as_text(entry.get("weather", "")) + " / " + as_text(entry.get("note", ""))
        py5.text(clip_to_width(meta, 240), 605, y + 17)

        y += 39


def draw_footer():
    py5.fill(150, 160, 151)
    py5.text_size(10)
    py5.text_align(py5.CENTER, py5.CENTER)
    py5.text("Everything goes into mood_entries.json next to this file. Nothing leaves your machine.",
             W / 2, 678)
    py5.text_align(py5.LEFT, py5.BASELINE)


def card(x, y, w, h):
    py5.no_stroke()
    py5.fill(226, 225, 216, 90)
    py5.rect(x + 2, y + 4, w, h, 18)
    py5.fill(255, 254, 250)
    py5.rect(x, y, w, h, 18)



def draw_mood_icon(index, x, y):
    c = MOOD_COLORS[index]
    py5.no_stroke()
    py5.fill(c[0], c[1], c[2])
    py5.ellipse(x, y, 25, 25)
    py5.fill(255, 255, 245)

    if index == 0 or index == 4:
        py5.ellipse(x - 4, y - 2, 2, 3)
        py5.ellipse(x + 4, y - 2, 2, 3)
        py5.no_fill()
        py5.stroke(255, 255, 245)
        py5.arc(x, y + 1, 10, 7, 0, py5.PI)
    elif index == 1:
        py5.ellipse(x - 4, y - 2, 2, 2)
        py5.ellipse(x + 4, y - 2, 2, 2)
        py5.no_fill()
        py5.stroke(255, 255, 245)
        py5.line(x - 4, y + 4, x + 4, y + 4)
    elif index == 2:
        py5.ellipse(x - 4, y - 2, 2, 2)
        py5.ellipse(x + 4, y - 2, 2, 2)
        py5.no_fill()
        py5.stroke(255, 255, 245)
        py5.arc(x, y + 8, 10, 8, py5.PI, py5.TWO_PI)
    else:
        py5.ellipse(x - 4, y - 2, 2, 2)
        py5.ellipse(x + 4, y - 2, 2, 2)
        py5.stroke(255, 255, 245)
        py5.line(x - 4, y + 5, x + 4, y + 2)

    py5.no_stroke()
    py5.no_fill()


def draw_weather_icon(index, x, y):
    py5.no_stroke()
    if index == 0:
        draw_sun(x, y, 11)
    elif index == 1:
        draw_cloud(x, y + 1, 0.45)
    elif index == 2:
        draw_cloud(x, y - 3, 0.42)
        py5.stroke(101, 157, 190)
        py5.stroke_weight(2)
        py5.line(x - 9, y + 9, x - 12, y + 15)
        py5.line(x, y + 9, x - 3, y + 15)
        py5.line(x + 9, y + 9, x + 6, y + 15)
        py5.no_stroke()
    else:
        py5.stroke(121, 169, 132)
        py5.stroke_weight(2)
        py5.no_fill()
        py5.arc(x, y - 3, 28, 15, py5.PI, py5.TWO_PI)
        py5.arc(x + 5, y + 4, 24, 12, 0, py5.PI)
        py5.no_stroke()
        py5.no_fill()


def draw_sun(x, y, radius):
    py5.no_stroke()
    py5.fill(245, 189, 83)
    py5.ellipse(x, y, radius * 2, radius * 2)

    py5.stroke(245, 189, 83)
    py5.stroke_weight(2)
    for angle in range(0, 360, 45):
        a = py5.radians(angle)
        py5.line(x + py5.cos(a) * (radius + 5), y + py5.sin(a) * (radius + 5),
                 x + py5.cos(a) * (radius + 10), y + py5.sin(a) * (radius + 10))
    py5.no_stroke()


def draw_cloud(x, y, s):
    py5.no_stroke()
    py5.fill(255, 255, 250)
    py5.ellipse(x - 12 * s, y, 24 * s, 18 * s)
    py5.ellipse(x, y - 6 * s, 25 * s, 25 * s)
    py5.ellipse(x + 13 * s, y, 23 * s, 17 * s)
    py5.rect(x - 17 * s, y - 1 * s, 34 * s, 10 * s, 5 * s)


def draw_leaf(x, y, s):
    py5.push_matrix()
    py5.translate(x, y)
    py5.rotate(-0.55)
    py5.no_stroke()
    py5.fill(111, 174, 132)
    py5.ellipse(0, 0, 24 * s, 43 * s)
    py5.stroke(242, 248, 235)
    py5.stroke_weight(1.5)
    py5.line(0, 17 * s, 0, -17 * s)
    py5.no_stroke()
    py5.pop_matrix()



def note_lines():
    global wrapped_lines, wrapped_for

    if wrapped_for == note:
        return wrapped_lines

    max_w = NOTE_W - 28
    lines = []
    cur = ""

    for ch in note:
        trial = cur + ch
        if py5.text_width(trial) <= max_w:
            cur = trial
            continue

        # No room left on this line. Back up to the last space so words stay whole.
        # CJK has no spaces, so those characters just break where they must.
        cut = cur.rfind(" ")
        if cut > 0:
            lines.append(cur[:cut])
            cur = cur[cut + 1:] + ch
        else:
            lines.append(cur)
            cur = ch

    lines.append(cur)
    wrapped_lines = lines
    wrapped_for = note
    return lines


def mouse_pressed():
    handle_click(py5.mouse_x, py5.mouse_y)


def key_pressed():
    handle_key(py5.key)


def handle_click(px, py):
    global mood_pick, weather_pick, typing, last_click_at

    # Save first, or the catch-all at the bottom of this function clears typing state
    # before the click is ever handled.
    if inside(px, py, SAVE_X, SAVE_Y, SAVE_W, SAVE_H):
        save_entry()
        typing = False
        return

    for i in range(len(MOODS)):
        x = 52 + (i % 3) * 151
        y = 214 + (i // 3) * 62
        if inside(px, py, x, y, 137, 49):
            mood_pick = i
            typing = False
            return

    for i in range(len(WEATHERS)):
        if inside(px, py, 52 + i * 113, 381, 101, 67):
            weather_pick = i
            typing = False
            return

    if inside(px, py, NOTE_X, NOTE_Y, NOTE_W, NOTE_H):
        typing = True
        # A second click within 350ms opens the dialog, for when you want to write at length.
        # last_click_at has to be checked against 0 first: millis() is also near zero right
        # after launch, so the very first click would otherwise count as a double click.
        if last_click_at > 0 and py5.millis() - last_click_at < 350:
            ask_for_note()
            last_click_at = 0
        else:
            last_click_at = py5.millis()
        return

    typing = False


def handle_key(k):
    global note

    if not typing:
        return

    # Arrow keys and bare Shift/Ctrl arrive as chr(65535). A plain k >= " " test stuffs that
    # into note, the counter goes up, nothing visible appears, and json gets a box character.
    if k is None or len(k) != 1:
        return

    if k == "\uffff":
        return

    if k == "\b" or k == "\x7f":
        note = note[:-1]
        return

    if k == "\n" or k == "\r":
        note += " "
        return

    if k == "\t":
        return

    if len(note) >= NOTE_LIMIT:
        return

    if ord(k) >= 32:
        note += k


def ask_for_note():
    """Open a system input dialog, for writing something longer than the box invites.

    This runs on CPython, so tkinter is already there and there is no need to reach for
    javax.swing the way the Processing build does.
    The dialog runs on a worker thread with no join, so the window keeps animating behind it
    instead of freezing until someone clicks OK.
    """
    global note, dialog_open

    if dialog_open:
        return
    dialog_open = True

    result = {}

    def worker():
        try:
            import tkinter as tk
            from tkinter import simpledialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            typed = simpledialog.askstring(
                "Mood Garden",
                "Write today's note (up to %d characters)" % NOTE_LIMIT,
                initialvalue=note,
                parent=root
            )
            root.destroy()
            result["text"] = typed
        except Exception as e:
            result["error"] = e
        finally:
            result["done"] = True

    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()
    # No join: the dialog does its thing while the canvas keeps drawing, and the text is
    # copied back once OK is pressed.
    threading.Thread(target=_collect_note, args=(result,), daemon=True).start()


def _collect_note(result):
    global note, dialog_open

    import time
    while not result.get("done"):
        time.sleep(0.05)

    dialog_open = False
    typed = result.get("text")
    if typed:
        note = typed[:NOTE_LIMIT]



def save_entry():
    global entries, status

    today = date.today().isoformat()
    text_note = note.strip()

    entry = {
        "date": today,
        "mood": MOODS[mood_pick],
        "weather": WEATHERS[weather_pick],
        "note": text_note if text_note != "" else "No note"
    }

    # One entry per day: drop today's old row, then put the new one in.
    # Non-dict junk is filtered out too, so a hand-edited json missing a comma does not
    # take the whole file down with it.
    kept = []
    for old in entries:
        if isinstance(old, dict) and old.get("date") != today:
            kept.append(old)
    kept.append(entry)
    kept.sort(key=sort_key)
    entries = kept

    # Python 3 takes the encoding directly, so no manual utf-8 byte juggling here.
    # ensure_ascii=False keeps Chinese readable in the file instead of \u4eca\u5929 soup.
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as handle:
            json.dump(entries, handle, indent=2, ensure_ascii=False)
    except Exception as e:
        status = "Save failed: " + str(e)
        return

    status = "Saved."


def load_entries():
    global entries, status

    entries = []
    if not DATA_FILE.exists():
        return

    try:
        with open(DATA_FILE, encoding="utf-8") as handle:
            loaded = json.load(handle)
    except Exception as e:
        # Say something when the file will not load, or it looks like the entries got wiped.
        status = "Can't read mood_entries.json: " + str(e)
        return

    if not isinstance(loaded, list):
        return

    for item in loaded:
        if isinstance(item, dict) and "date" in item:
            entries.append(item)
    entries.sort(key=sort_key)


def restore_today():
    # If today is already saved, load it back into the form. Editing beats retyping.
    global mood_pick, weather_pick, note, status

    today = date.today().isoformat()
    found = find_entry(today)
    if found is None:
        return

    idx = mood_index_for(found.get("mood", ""))
    if idx >= 0:
        mood_pick = idx

    idx = weather_index_for(found.get("weather", ""))
    if idx >= 0:
        weather_pick = idx

    saved = found.get("note", "")
    if saved != "No note":
        # Trimmed, because the counter says 80 and a stale or hand-edited file can hold more.
        # Left whole, the counter reads 173 / 80 and typing stops making sense.
        note = saved[:NOTE_LIMIT]

    status = "Today is saved. Save again to update it."


def sort_key(entry):
    return entry.get("date", "")


def find_entry(iso_date):
    for entry in entries:
        if entry.get("date") == iso_date:
            return entry
    return None


def as_text(value):
    # json already hands back str here; this only guards against None
    if value is None:
        return ""
    return str(value)


def clip_to_width(s, max_w):
    # Cut by measured pixel width. Counting characters is wrong: a CJK glyph is about twice
    # as wide as a Latin one, and 38 of them burst the card on the right.
    if py5.text_width(s) <= max_w:
        return s
    out = s
    while len(out) > 0 and py5.text_width(out + "...") > max_w:
        out = out[:-1]
    return out + "..."


def mood_index_for(name):
    for i in range(len(MOODS)):
        if MOODS[i] == name:
            return i
    return -1


def weather_index_for(name):
    for i in range(len(WEATHERS)):
        if WEATHERS[i] == name:
            return i
    return -1



def inside(px, py, x, y, w, h):
    return x <= px <= x + w and y <= py <= y + h


def over_rect(x, y, w, h):
    return inside(py5.mouse_x, py5.mouse_y, x, y, w, h)


# Opens the window. py5 keeps it alive until it is closed.
py5.run_sketch()
