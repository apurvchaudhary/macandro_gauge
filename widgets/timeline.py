from datetime import datetime, timedelta

from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView

from colors import (
    TEXT_SUBTLE,
    SCHEDULE_HOUR_LINE,
    EVENT_BLOCK_BG_ALT,
    EVENT_BLOCK_TEXT,
    EVENT_BORDER_SHADOW,
    BG_MODAL,
)


def parse_iso_to_local(value):
    if not value:
        return None
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        try:
            from dateutil import parser
            dt = parser.isoparse(s)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone()


class DayScheduleView(FloatLayout):
    def __init__(self, events: list, day_date: datetime, **kwargs):
        super().__init__(**kwargs)
        self.events = events or []
        self.day_date = day_date
        self.dp_per_min = dp(1)
        self.left_pad = dp(50)
        self.right_pad = dp(10)
        self.hour_color = SCHEDULE_HOUR_LINE
        self.event_text_color = EVENT_BLOCK_TEXT
        self.content_height = int(24 * 60 * self.dp_per_min)
        self.size_hint_y = None
        self.height = self.content_height
        self.bind(size=self._redraw, pos=self._redraw)
        Clock.schedule_once(self._redraw, 0)
        Clock.schedule_interval(self._update_now_line, 1 / 30.0)

    @staticmethod
    def _layout_events(items):
        items.sort(key=lambda x: (x[0], x[1]))
        groups = []
        current = []
        current_end = -1
        for s, e, ev in items:
            if s > current_end:
                if current:
                    groups.append(current)
                current = [(s, e, ev)]
                current_end = e
            else:
                current.append((s, e, ev))
                current_end = max(current_end, e)
        if current:
            groups.append(current)
        laid = []
        for group in groups:
            cols = []
            base_index = len(laid)
            for s, e, ev in sorted(group, key=lambda x: (x[0], x[1])):
                placed = False
                for ci, last_end in enumerate(cols):
                    if s >= last_end:
                        cols[ci] = e
                        laid.append((s, e, ev, ci, len(cols)))
                        placed = True
                        break
                if not placed:
                    cols.append(e)
                    ci = len(cols) - 1
                    laid.append((s, e, ev, ci, len(cols)))
            total_cols = len(cols)
            for i in range(base_index, len(laid)):
                s, e, ev, ci, tc = laid[i]
                laid[i] = (s, e, ev, ci, total_cols)
        return laid

    def _redraw(self, *args):
        self.canvas.clear()
        for child in list(self.children):
            self.remove_widget(child)

        def y_for_min(mins: int) -> float:
            return self.content_height - (mins * self.dp_per_min)

        with self.canvas:
            Color(*self.hour_color)
            for h in range(25):
                y = y_for_min(h * 60)
                Line(points=[self.left_pad, y, self.width - self.right_pad, y], width=1)

        for h in range(24):
            y = y_for_min(h * 60)
            lbl = Label(text=f"{h:02d}:00", color=TEXT_SUBTLE, size_hint=(None, None), size=(self.left_pad - dp(8), dp(16)))
            lbl.pos = (dp(4), y - dp(8))
            self.add_widget(lbl)

        items = []
        day_start = self.day_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone()
        day_end = day_start + timedelta(days=1)
        for ev in self.events:
            s = parse_iso_to_local(ev.get("from"))
            e = parse_iso_to_local(ev.get("to")) or s
            if not s:
                continue
            if e <= day_start or s >= day_end:
                continue
            s_clip = max(s, day_start)
            e_clip = min(e, day_end)
            s_min = int((s_clip - day_start).total_seconds() // 60)
            e_min = max(s_min + 5, int((e_clip - day_start).total_seconds() // 60))
            items.append((s_min, e_min, ev))

        laid = self._layout_events(items)
        for s_min, e_min, ev, col_idx, total_cols in laid:
            top = y_for_min(s_min)
            bottom = y_for_min(e_min)
            width = self.width - self.left_pad - self.right_pad
            col_w = width / max(1, total_cols)
            x = self.left_pad + col_idx * col_w + dp(2)
            w = col_w - dp(4)
            y = bottom + dp(1)
            h = max(dp(18), top - bottom - dp(2))
            with self.canvas:
                Color(*EVENT_BLOCK_BG_ALT)
                Rectangle(pos=(x, y), size=(w, h))
                Color(*EVENT_BORDER_SHADOW)
                Line(rectangle=(x, y, w, h), width=1)
            box = Label(text=f"[b]{ev.get('title','(No title)')}[/b]\n{ev.get('organizer','')}", markup=True, halign='left', valign='top', color=self.event_text_color)
            box.size_hint = (None, None)
            box.text_size = (w - dp(4), h - dp(4))
            box.size = (w, h)
            box.pos = (x + dp(2), y + dp(2))
            self.add_widget(box)

    def _update_now_line(self, dt):
        now = datetime.now().astimezone()
        if now.date() == self.day_date.date():
            # Only update the now line (redraw minimal part)
            self._redraw()


class DayScheduleModal(ModalView):
    def __init__(self, events: list, day_date: datetime, **kwargs):
        super().__init__(size_hint=(0.98, 0.98), auto_dismiss=True, background_color=BG_MODAL, **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        header = Label(
            text=day_date.strftime("%A, %d %B %Y"),
            size_hint_y=None,
            height=dp(30),
            color=TEXT_SUBTLE,
            font_size="18sp"
        )
        root.add_widget(header)

        sc = ScrollView(size_hint=(1, 1))
        timeline = DayScheduleView(events, day_date)
        sc.add_widget(timeline)
        root.add_widget(sc)
        self.add_widget(root)

        def scroll_to_10am(*args):
            total_height = timeline.content_height
            y_10am = 10 * 60 * timeline.dp_per_min
            scroll_y = 1 - (y_10am / total_height)
            sc.scroll_y = max(0, min(1, scroll_y))

        Clock.schedule_once(scroll_to_10am, 0.3)
