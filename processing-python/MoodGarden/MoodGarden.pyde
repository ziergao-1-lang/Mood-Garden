# -*- coding: utf-8 -*-
# Mood Garden: a small notebook for how a day felt
# Processing Python Mode (Processing 3 or 4, once Python Mode is installed, just open and run)
#
# How to use it: pick a mood, pick the weather, write a couple of lines, press save.
# Entries land in mood_entries.json inside this sketch folder. One per day; saving again
# rewrites today's entry rather than adding another.
#
# One caveat up front: Processing's keyPressed never sees IME composition.
# So typing straight into the box only gets you Latin characters and punctuation. To write
# Chinese, double-click the box; that opens a system dialog, and that one handles the IME.

import json
import os
from datetime import date, timedelta

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

entries = []
mood_pick = 0
weather_pick = 0
note = ""
typing = False
status = ""
last_click_at = 0

# Wrapping is cached. As long as note is unchanged there is no reason to measure textWidth
# again, and doing it for every character on every frame costs real frames.
wrapped_lines = []
wrapped_for = None


def setup():
    size(W, H)
    smooth(4)
    setTitle("Mood Garden")
    textFont(pick_font())
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
    # glyphs rather than getting a row of boxes. Falls back to Java's default logical font.
    names = []
    try:
        for name in PFont.list():
            names.append(str(name))
    except Exception:
        names = []

    for want in ["Microsoft YaHei", "PingFang SC", "Hiragino Sans GB",
                 "Noto Sans CJK SC", "Source Han Sans CN",
                 "WenQuanYi Micro Hei", "SimHei"]:
        if want in names:
            return createFont(want, 15)

    return createFont("SansSerif", 15)



def draw_background():
    background(247, 246, 239)
    noStroke()
    fill(228, 240, 230)
    ellipse(850, 20, 220, 180)
    fill(239, 228, 207)
    ellipse(35, 680, 180, 150)


def draw_header():
    fill(42, 66, 62)
    textSize(30)
    textAlign(LEFT, BASELINE)
    text("Mood Garden", 36, 52)

    fill(110, 128, 119)
    textSize(14)
    text("One line a day. No streaks to keep.", 38, 77)

    draw_sun(809, 49, 19)
    draw_cloud(843, 65, 0.72)


def draw_form():
    card(30, 105, 510, 515)

    fill(42, 66, 62)
    textSize(18)
    textAlign(LEFT, BASELINE)
    text("Today's check-in", 52, 139)

    fill(120, 137, 128)
    textSize(12)
    text(date.today().strftime("%a, %d %b %Y").upper(), 52, 161)


def draw_moods():
    fill(55, 76, 69)
    textSize(14)
    textAlign(LEFT, BASELINE)
    text("Pick the mood that's closest", 52, 197)

    for i in range(len(MOODS)):
        x = 52 + (i % 3) * 151
        # Integer division on purpose. Under Jython 2.7 i / 3 happens to be integer too,
        # but the moment this runs on Python 3 it turns into a float. Spelling // avoids that.
        y = 214 + (i // 3) * 62
        picked = (i == mood_pick)
        hovered = over_rect(x, y, 137, 49)

        if picked:
            fill(232, 243, 235)
            stroke(MOOD_COLORS[i][0], MOOD_COLORS[i][1], MOOD_COLORS[i][2])
        elif hovered:
            fill(250, 249, 244)
            stroke(190, 207, 195)
        else:
            fill(255, 254, 250)
            stroke(230, 229, 220)
        strokeWeight(1.2)
        rect(x, y, 137, 49, 12)
        noStroke()

        draw_mood_icon(i, x + 25, y + 24)

        fill(54, 72, 66)
        textSize(13)
        textAlign(LEFT, CENTER)
        text(MOODS[i], x + 45, y + 25)

    textAlign(LEFT, BASELINE)


def draw_weather():
    fill(55, 76, 69)
    textSize(14)
    textAlign(LEFT, BASELINE)
    text("And the weather?", 52, 365)

    for i in range(len(WEATHERS)):
        x = 52 + i * 113
        y = 381
        if i == weather_pick:
            fill(232, 243, 235)
            stroke(103, 164, 142)
        else:
            fill(255, 254, 250)
            stroke(230, 229, 220)
        strokeWeight(1)
        rect(x, y, 101, 67, 12)
        noStroke()

        draw_weather_icon(i, x + 50, y + 23)

        fill(74, 94, 85)
        textSize(11)
        textAlign(CENTER, CENTER)
        text(WEATHERS[i], x + 50, y + 52)

    textAlign(LEFT, BASELINE)


def draw_note_box():
    fill(55, 76, 69)
    textSize(14)
    textAlign(LEFT, BASELINE)
    text("A note to yourself", NOTE_X, 475)

    # Counter sits on the title row instead of inside the box, where it would fight the text.
    fill(150, 160, 151)
    textSize(10)
    textAlign(RIGHT, BASELINE)
    text(str(len(note)) + " / " + str(NOTE_LIMIT), NOTE_X + NOTE_W, 475)
    textAlign(LEFT, BASELINE)

    if typing:
        fill(255, 255, 252)
        stroke(93, 164, 142)
        strokeWeight(1.5)
    else:
        fill(255, 254, 250)
        stroke(230, 229, 220)
        strokeWeight(1)
    rect(NOTE_X, NOTE_Y, NOTE_W, NOTE_H, 11)
    noStroke()

    if note == "":
        fill(160, 169, 160)
        textSize(12)
        text("Click here and type, or double-click for Chinese",
             NOTE_X + 14, NOTE_Y + 26)
        return

    # Set the body size before wrapping. note_lines() measures with textWidth, and if it runs
    # while the size is still 10 from the counter above, it thinks more fits per line than does.
    # The result is text drawn at 13 that runs straight out of the box.
    fill(65, 82, 73)
    textSize(13)
    lines = note_lines()
    for i in range(len(lines)):
        text(lines[i], NOTE_X + 14, NOTE_Y + NOTE_TEXT_TOP + i * LINE_H)

    # Blinking caret, otherwise there is no sign the box is taking input.
    if typing and (millis() // 500) % 2 == 0:
        last = lines[len(lines) - 1]
        cx = NOTE_X + 14 + textWidth(last) + 1
        cy = NOTE_Y + NOTE_TEXT_TOP + (len(lines) - 1) * LINE_H
        stroke(93, 164, 142)
        strokeWeight(1.5)
        line(cx, cy - 11, cx, cy + 3)
        noStroke()


def draw_save_row():
    hovered = over_rect(SAVE_X, SAVE_Y, SAVE_W, SAVE_H)
    noStroke()
    if hovered:
        fill(46, 112, 94)
    else:
        fill(62, 131, 111)
    rect(SAVE_X, SAVE_Y, SAVE_W, SAVE_H, 10)

    fill(255, 255, 255)
    textSize(12)
    textAlign(CENTER, CENTER)
    text("Save today's mood", SAVE_X + SAVE_W / 2, SAVE_Y + SAVE_H / 2)

    if status != "":
        fill(104, 130, 118)
        textSize(11)
        textAlign(LEFT, CENTER)
        text(status, SAVE_X + SAVE_W + 14, SAVE_Y + SAVE_H / 2)

    textAlign(LEFT, BASELINE)


def draw_week_card():
    card(560, 105, 310, 242)

    fill(42, 66, 62)
    textSize(17)
    textAlign(LEFT, BASELINE)
    text("Mood by day", 582, 139)

    fill(116, 135, 126)
    textSize(11)
    text("Last 7 days", 582, 159)

    chart_x = 590
    chart_y = 190
    chart_h = 112
    chart_w = 252

    stroke(229, 231, 222)
    strokeWeight(1)
    line(chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h)
    noStroke()

    for offset in range(6, -1, -1):
        day = date.today() - timedelta(days=offset)
        i = 6 - offset
        found = find_entry(day.isoformat())

        x = chart_x + 9 + i * 35

        if found is None:
            fill(228, 230, 222)
            rect(x, chart_y + chart_h - 8, 22, 8, 5)
        else:
            idx = mood_index_for(found.get("mood", ""))
            if idx < 0:
                fill(200, 200, 195)
            else:
                c = MOOD_COLORS[idx]
                fill(c[0], c[1], c[2])
            # Fixed height. A bar means the day got a page, nothing about how strong the mood was.
            rect(x, chart_y + chart_h - 48, 22, 48, 6)
            ellipse(x + 11, chart_y + chart_h - 53, 10, 10)

        fill(119, 135, 124)
        textSize(9)
        textAlign(CENTER, CENTER)
        text(day.strftime("%a")[:1], x + 11, chart_y + chart_h + 16)

    textAlign(LEFT, BASELINE)
    fill(119, 135, 124)
    textSize(10)
    # This caption used to sit at 333, two pixels under the weekday letters, and read as
    # one smudged line. Moved down to 339.
    text("A bar just means a page got written that day.", 582, 339)


def draw_recent_card():
    card(560, 365, 310, 255)

    fill(42, 66, 62)
    textSize(17)
    textAlign(LEFT, BASELINE)
    text("Recent pages", 582, 399)

    if len(entries) == 0:
        draw_leaf(608, 470, 1.0)
        fill(119, 135, 124)
        textSize(12)
        text("Nothing saved yet.", 632, 465)
        text("Today's check-in is on the left.", 632, 486)
        return

    y = 431
    for entry in entries[-5:][::-1]:
        idx = mood_index_for(entry.get("mood", ""))
        if idx < 0:
            fill(200, 200, 195)
        else:
            c = MOOD_COLORS[idx]
            fill(c[0], c[1], c[2])
        ellipse(590, y - 4, 10, 10)

        fill(57, 77, 68)
        textSize(12)
        textAlign(LEFT, BASELINE)
        text(as_text(entry.get("mood", "?")), 605, y)

        fill(137, 151, 141)
        textSize(10)
        textAlign(RIGHT, BASELINE)
        text(as_text(entry.get("date", "")), 848, y)
        textAlign(LEFT, BASELINE)

        fill(110, 127, 118)
        textSize(10)
        meta = as_text(entry.get("weather", "")) + u" / " + as_text(entry.get("note", ""))
        text(clip_to_width(meta, 240), 605, y + 17)

        y += 39


def draw_footer():
    fill(150, 160, 151)
    textSize(10)
    textAlign(CENTER, CENTER)
    text("Everything goes into mood_entries.json next to this sketch. Nothing leaves your machine.",
         W / 2, 678)
    textAlign(LEFT, BASELINE)


def card(x, y, w, h):
    noStroke()
    fill(226, 225, 216, 90)
    rect(x + 2, y + 4, w, h, 18)
    fill(255, 254, 250)
    rect(x, y, w, h, 18)



def draw_mood_icon(index, x, y):
    c = MOOD_COLORS[index]
    noStroke()
    fill(c[0], c[1], c[2])
    ellipse(x, y, 25, 25)
    fill(255, 255, 245)

    if index == 0 or index == 4:
        ellipse(x - 4, y - 2, 2, 3)
        ellipse(x + 4, y - 2, 2, 3)
        noFill()
        stroke(255, 255, 245)
        arc(x, y + 1, 10, 7, 0, PI)
    elif index == 1:
        ellipse(x - 4, y - 2, 2, 2)
        ellipse(x + 4, y - 2, 2, 2)
        noFill()
        stroke(255, 255, 245)
        line(x - 4, y + 4, x + 4, y + 4)
    elif index == 2:
        ellipse(x - 4, y - 2, 2, 2)
        ellipse(x + 4, y - 2, 2, 2)
        noFill()
        stroke(255, 255, 245)
        arc(x, y + 8, 10, 8, PI, TWO_PI)
    else:
        ellipse(x - 4, y - 2, 2, 2)
        ellipse(x + 4, y - 2, 2, 2)
        stroke(255, 255, 245)
        line(x - 4, y + 5, x + 4, y + 2)

    noStroke()
    noFill()


def draw_weather_icon(index, x, y):
    noStroke()
    if index == 0:
        draw_sun(x, y, 11)
    elif index == 1:
        draw_cloud(x, y + 1, 0.45)
    elif index == 2:
        draw_cloud(x, y - 3, 0.42)
        stroke(101, 157, 190)
        strokeWeight(2)
        line(x - 9, y + 9, x - 12, y + 15)
        line(x, y + 9, x - 3, y + 15)
        line(x + 9, y + 9, x + 6, y + 15)
        noStroke()
    else:
        stroke(121, 169, 132)
        strokeWeight(2)
        noFill()
        arc(x, y - 3, 28, 15, PI, TWO_PI)
        arc(x + 5, y + 4, 24, 12, 0, PI)
        noStroke()
        noFill()


def draw_sun(x, y, radius):
    noStroke()
    fill(245, 189, 83)
    ellipse(x, y, radius * 2, radius * 2)

    stroke(245, 189, 83)
    strokeWeight(2)
    for angle in range(0, 360, 45):
        a = radians(angle)
        line(x + cos(a) * (radius + 5), y + sin(a) * (radius + 5),
             x + cos(a) * (radius + 10), y + sin(a) * (radius + 10))
    noStroke()


def draw_cloud(x, y, s):
    noStroke()
    fill(255, 255, 250)
    ellipse(x - 12 * s, y, 24 * s, 18 * s)
    ellipse(x, y - 6 * s, 25 * s, 25 * s)
    ellipse(x + 13 * s, y, 23 * s, 17 * s)
    rect(x - 17 * s, y - 1 * s, 34 * s, 10 * s, 5 * s)


def draw_leaf(x, y, s):
    pushMatrix()
    translate(x, y)
    rotate(-0.55)
    noStroke()
    fill(111, 174, 132)
    ellipse(0, 0, 24 * s, 43 * s)
    stroke(242, 248, 235)
    strokeWeight(1.5)
    line(0, 17 * s, 0, -17 * s)
    noStroke()
    popMatrix()



def note_lines():
    global wrapped_lines, wrapped_for

    if wrapped_for == note:
        return wrapped_lines

    max_w = NOTE_W - 28
    lines = []
    cur = ""

    for ch in note:
        trial = cur + ch
        if textWidth(trial) <= max_w:
            cur = trial
            continue

        # No room left on this line. Back up to the last space so words stay whole.
        # CJK has no spaces, so those characters just break where they must.
        cut = cur.rfind(u" ")
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


def mousePressed():
    # Processing's callback only hands over the mouse position.
    # The actual hit testing lives in handle_click, because it does not read the global mouseX,
    # so a test script can call it with any coordinate, and both builds share the same one.
    handle_click(mouseX, mouseY)


def keyPressed():
    handle_key(key)


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
        # A second click opens the system dialog. For Chinese this is the only route in;
        # Processing's own keyboard callback never sees the IME.
        # last_click_at has to be checked against 0 first: millis() is also near zero right
        # after launch, so the very first click would otherwise count as a double click.
        if last_click_at > 0 and millis() - last_click_at < 350:
            ask_for_note()
            last_click_at = 0
        else:
            last_click_at = millis()
        return

    typing = False


def handle_key(k):
    global note

    if not typing:
        return

    if k is None or len(k) != 1:
        return

    # Arrow keys and bare Shift/Ctrl arrive as chr(65535). A plain key >= " " test stuffs that
    # into note, the counter goes up, nothing visible appears, and json gets a box character.
    if k == u"\uffff":
        return

    if k == u"\b" or k == u"\x7f":
        note = note[:-1]
        return

    if k == u"\n" or k == u"\r":
        note += u" "
        return

    if k == u"\t":
        return

    if len(note) >= NOTE_LIMIT:
        return

    if ord(k) >= 32:
        note += k


def ask_for_note():
    global note

    try:
        from javax.swing import JOptionPane
    except Exception:
        # No Swing available, carry on. Latin typing still works.
        return

    try:
        typed = JOptionPane.showInputDialog(
            None,
            u"Write today's note (up to " + str(NOTE_LIMIT) + u" characters)",
            u"Mood Garden",
            JOptionPane.PLAIN_MESSAGE,
            None,
            None,
            note
        )
    except Exception:
        return

    if typed is None:
        return

    # What comes back is a Java String. Concatenating it in Python routes through the default
    # codec, and under Jython that is ascii, so Chinese explodes on the spot. Going via utf-8
    # bytes sidesteps the whole thing.
    try:
        typed = typed.encode("utf-8").decode("utf-8")
    except Exception:
        return

    note = typed[:NOTE_LIMIT]



def save_entry():
    global entries, status

    today = date.today().isoformat()
    text_note = note.strip()

    entry = {
        "date": today,
        "mood": MOODS[mood_pick],
        "weather": WEATHERS[weather_pick],
        "note": text_note if text_note != u"" else u"No note"
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

    # Binary mode, encoding done by hand.
    # In text mode Jython encodes with the default (ascii), and the day someone writes Chinese
    # it dies. Encoding here also means the file shows Chinese instead of \u4eca\u5929.
    try:
        payload = json.dumps(entries, indent=2, ensure_ascii=False)
        handle = open(data_path(), "wb")
        try:
            handle.write(payload.encode("utf-8"))
        finally:
            handle.close()
    except Exception as e:
        status = "Save failed: " + str(e)
        return

    status = "Saved."


def load_entries():
    global entries, status

    entries = []
    path = data_path()
    if not os.path.exists(path):
        return

    try:
        handle = open(path, "rb")
        try:
            raw = handle.read()
        finally:
            handle.close()
        loaded = json.loads(raw.decode("utf-8"))
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


def data_path():
    return os.path.join(sketchPath(), "mood_entries.json")


def as_text(value):
    # Fields out of json may be str or unicode, and a bare str() on Chinese would encode
    # with ascii and raise. Everything goes through utf-8 into unicode first.
    if value is None:
        return u""
    if isinstance(value, type(u"")):
        return value
    try:
        return value.encode("utf-8").decode("utf-8")
    except Exception:
        return u""


def clip_to_width(s, max_w):
    # Cut by measured pixel width. Counting characters is wrong: a CJK glyph is about twice
    # as wide as a Latin one, and 38 of them burst the card on the right.
    if textWidth(s) <= max_w:
        return s
    out = s
    while len(out) > 0 and textWidth(out + u"...") > max_w:
        out = out[:-1]
    return out + u"..."


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
    return inside(mouseX, mouseY, x, y, w, h)
