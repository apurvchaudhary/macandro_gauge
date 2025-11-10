import calendar as pycalendar
from datetime import datetime, timedelta
from importlib import import_module
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform as core_platform
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.list import MDList, TwoLineListItem

from colors import (
    TEXT_PRIMARY,
    TEXT_SUBTLE,
    CAL_WEEKDAY_HDR,
    CAL_DAY_NORMAL,
    CAL_DAY_NORMAL_ALT,
    CAL_DAY_TODAY,
    BG_MODAL,
    SCHEDULE_HOUR_LINE,
    EVENT_BLOCK_BG,
    EVENT_BLOCK_BG_ALT,
    EVENT_BLOCK_TEXT,
    EVENT_BORDER_SHADOW,
    NOW_LINE,
    CLOCK_LOCAL_COLOR,
    CLOCK_TZ_COLOR,
    EVENT_HIGHLIGHT,
)
from gauge import Gauge

autoclass = None
# Optional: plyer for portable keep-awake
plyer_keepawake = None
try:
    plyer = import_module("plyer")
    if hasattr(plyer, "keepawake"):
        plyer_keepawake = plyer.keepawake
except Exception:
    # plyer may not be available on all platforms
    plyer_keepawake = None

# Optional: Pyjnius for Android window flags as redundancy
try:
    from jnius import autoclass
except Exception:
    autoclass = None


KV = """
#:import dp kivy.metrics.dp
MDBoxLayout:
    orientation: "vertical"
    padding: dp(8)
    spacing: dp(10)

    MDGridLayout:
        id: top_row
        cols: 4
        adaptive_height: True
        spacing: dp(8)
        row_default_height: dp(200)
        row_force_default: True

    MDGridLayout:
        id: bottom_row
        cols: 3
        spacing: dp(8)
        size_hint_y: None
        height: dp(200)
"""

BASE_URL = "http://192.168.1.30:8001"


class DigitalClock(BoxLayout):
    """A sleek digital clock with timezone support."""

    def __init__(self, tz: str = "local", title: str = "Clock", **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(6), **kwargs)
        self.tz = tz
        color = CLOCK_LOCAL_COLOR if tz == "local" else CLOCK_TZ_COLOR
        self.title = Label(text=title, color=color, font_size="16sp", size_hint_y=None, height=dp(18))
        self.time_lbl = Label(text="--:--:--", font_size="50sp", markup=True, color=color)
        self.add_widget(self.title)
        self.add_widget(self.time_lbl)
        Clock.schedule_interval(self._tick, 1)
        self._tick(0)

    def _get_now(self):
        if self.tz == "local":
            return datetime.now()
        try:
            return datetime.now(ZoneInfo(self.tz))
        except (ZoneInfoNotFoundError, Exception):
            return datetime.now()

    def _tick(self, dt):
        now = self._get_now()
        self.time_lbl.text = now.strftime("%H:%M:%S")


class MonthCalendar(BoxLayout):
    """A minimal monthly calendar that highlights today, supports swiping, and opens a big modal on tap."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(6), **kwargs)
        self.title = Label(
            text="Calendar", color=TEXT_SUBTLE, font_size="18sp", size_hint_y=None, height=dp(24)
        )
        self.header = Label(text="", font_size="20sp", color=TEXT_PRIMARY, size_hint_y=None, height=dp(28))
        self.grid = None
        # Track which month/year are displayed
        today = datetime.now()
        self.display_year = today.year
        self.display_month = today.month
        # Track touch for swipe/tap
        self._touch_start = None
        self._tap_opened = False
        self.add_widget(self.title)
        self.add_widget(self.header)
        self._build()
        # Refresh periodically only when viewing the current month
        Clock.schedule_interval(self._maybe_refresh, 60)

    def _set_month(self, year: int, month: int):
        # Normalize year/month to 1..12
        y, m = year, month
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        self.display_year, self.display_month = y, m
        self._build()

    def _shift_month(self, delta: int):
        self._set_month(self.display_year, self.display_month + delta)

    def _build(self):
        # Remove the old grid if present
        if self.grid is not None:
            self.remove_widget(self.grid)
            self.grid = None
        from kivy.uix.gridlayout import GridLayout

        # Update month header
        year, month = self.display_year, self.display_month
        self.header.text = pycalendar.month_name[month] + f" {year}"
        # Build a new grid
        self.grid = GridLayout(cols=7, rows=7, spacing=dp(4))
        # Weekday headers (Mon-Sun)
        for wd in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            self.grid.add_widget(Label(text=wd, color=CAL_WEEKDAY_HDR))
        # Month days
        cal = pycalendar.Calendar(firstweekday=0)  # Monday
        today = datetime.now()
        for week in cal.monthdayscalendar(year, month):
            for day in week:
                if day == 0:
                    self.grid.add_widget(Label(text=""))
                else:
                    # Highlight today only if the displayed month is the current month
                    is_today = (year == today.year and month == today.month and day == today.day)
                    txt = f"[b]{day}[/b]" if is_today else str(day)
                    col = CAL_DAY_TODAY if is_today else CAL_DAY_NORMAL
                    self.grid.add_widget(Label(text=txt, markup=True, color=col))
        self.add_widget(self.grid)

    def _maybe_refresh(self, dt):
        # Only refresh when displaying the real current month, so the 'today' highlight stays correct
        now = datetime.now()
        if self.display_year == now.year and self.display_month == now.month:
            self._build()

    # --- Swipe handling ---
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start = touch.pos
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        handled = False
        if self._touch_start and self.collide_point(*touch.pos):
            sx, sy = self._touch_start
            dx = touch.x - sx
            dy = touch.y - sy
            threshold = dp(60)
            vertical_limit = dp(80)
            if abs(dx) > threshold and abs(dy) < vertical_limit:
                if dx < 0:
                    # Swipe left -> next month
                    self._shift_month(+1)
                else:
                    # Swipe right -> previous month
                    self._shift_month(-1)
                handled = True
            else:
                # Consider as a tap: open enlarged calendar modal
                try:
                    app = App.get_running_app()
                    if hasattr(app, "open_calendar_modal"):
                        app.open_calendar_modal(self.display_year, self.display_month)
                        handled = True
                except Exception:
                    pass
        self._touch_start = None
        if handled:
            return True
        return super().on_touch_up(touch)


class EventsPanel(BoxLayout):
    """Scrollable list of events from the API; highlights the next event."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(6), **kwargs)
        self.title = Label(text="Events", color=TEXT_SUBTLE, font_size="16sp", size_hint_y=None, height=dp(24))
        self.add_widget(self.title)
        # Scrollable list
        self.scroll = ScrollView(size_hint=(1, 1))
        self.list = MDList()
        self.scroll.add_widget(self.list)
        self.add_widget(self.scroll)

    @staticmethod
    def _parse_dt(value: str):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                return dt.astimezone()  # treat as local naive
            return dt.astimezone()  # convert to local tz
        except Exception:
            return None

    @staticmethod
    def _format_slot(start: datetime, end: datetime, location: str | None):
        if not start:
            return ""
        local_now = datetime.now().astimezone()
        same_day = start.date() == local_now.date()
        time_part = start.strftime("%H:%M")
        end_part = end.strftime("%H:%M") if end else ""
        date_part = "Today" if same_day else start.strftime("%a, %d %b")
        loc_part = f" · {location}" if location else ""
        # e.g., Today 16:30-18:00 · Room
        if end_part:
            return f"{date_part} {time_part}-{end_part}{loc_part}"
        return f"{date_part} {time_part}{loc_part}"

    def _add_empty(self) -> None:
        """Show the fallback empty state in the events list."""
        self.list.add_widget(TwoLineListItem(text="No upcoming events", secondary_text=""))

    def update_events(self, events: list):
        # Clear the current list
        self.list.clear_widgets()
        if not events:
            self._add_empty()
            return

        local_now = datetime.now().astimezone()
        items = []
        for ev in events:
            start = self._parse_dt(ev.get("from"))
            end = self._parse_dt(ev.get("to"))
            if start is None and end is None:
                continue
            # Use start for sorting; if missing, use the end
            sort_key = start or end or local_now
            # Filter: show if the event is ongoing or in the future (end >= now)
            show = False
            if end is not None:
                show = end >= local_now
            elif start is not None:
                show = start >= local_now
            if not show:
                continue
            items.append((sort_key, ev, start, end))

        if not items:
            self._add_empty()
            return

        # Sort by start time ascending
        items.sort(key=lambda x: x[0])

        # Add to the list, highlighting the first item as the main event
        for idx, (_, ev, start, end) in enumerate(items):
            title = ev.get("title") or "(No title)"
            secondary = self._format_slot(start, end, ev.get("location"))
            li = TwoLineListItem(text=title, secondary_text=secondary)
            if idx == 0:
                # Highlight the next/ongoing event
                try:
                    li.theme_text_color = "Custom"
                    li.text_color = EVENT_HIGHLIGHT
                except Exception:
                    pass
            self.list.add_widget(li)


class DayCell(ButtonBehavior, Label):
    """Clickable day cell used in the enlarged calendar."""
    def __init__(self, day:int, is_today:bool, on_pick, **kwargs):
        super().__init__(**kwargs)
        self.day = day
        self.markup = True
        self.text = f"[b]{day}[/b]" if is_today else str(day)
        self.color = CAL_DAY_TODAY if is_today else CAL_DAY_NORMAL_ALT
        self.on_pick = on_pick
        self.font_size = "20sp"
        self.size_hint_y = None
        self.height = dp(40)

    def on_release(self):
        if callable(self.on_pick):
            self.on_pick(self.day)


class BigCalendarModal(ModalView):
    """Full-screen month calendar modal allowing date selection."""
    def __init__(self, year:int, month:int, on_select, **kwargs):
        super().__init__(size_hint=(0.95, 0.95), auto_dismiss=True, background_color=BG_MODAL)
        self.bg_color = BG_MODAL
        self.canvas.before.add(Color(*self.bg_color))
        self.canvas.before.add(Line(rectangle=(0,0,0,0)))
        self.on_select = on_select
        self.year = year
        self.month = month
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        header = Label(text=f"{pycalendar.month_name[month]} {year}", font_size="22sp", color=TEXT_PRIMARY, size_hint_y=None, height=dp(30))
        root.add_widget(header)
        from kivy.uix.gridlayout import GridLayout
        grid = GridLayout(cols=7, rows=7, spacing=dp(6))
        for wd in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:
            grid.add_widget(Label(text=wd, color=CAL_WEEKDAY_HDR))
        cal = pycalendar.Calendar(firstweekday=0)
        today = datetime.now()
        def pick(day):
            if callable(self.on_select):
                self.dismiss()
                self.on_select(datetime(year, month, day))
        for week in cal.monthdayscalendar(year, month):
            for day in week:
                if day == 0:
                    grid.add_widget(Label(text=""))
                else:
                    is_today = (year==today.year and month==today.month and day==today.day)
                    grid.add_widget(DayCell(day, is_today, pick))
        root.add_widget(grid)
        self.add_widget(root)


class DayScheduleView(FloatLayout):
    """Renders a 24h timeline with horizontal hour lines and event blocks."""
    def __init__(self, events: list, day_date: datetime, **kwargs):
        super().__init__(**kwargs)
        self.events = events or []
        self.day_date = day_date
        self.dp_per_min = dp(1)  # 60dp per hour
        self.left_pad = dp(50)
        self.right_pad = dp(10)
        self.hour_color = SCHEDULE_HOUR_LINE
        self.event_color = EVENT_BLOCK_BG
        self.event_text_color = EVENT_BLOCK_TEXT
        self.content_height = int(24*60*self.dp_per_min)
        self.size_hint_y = None
        self.height = self.content_height
        self.bind(size=self._redraw, pos=self._redraw)
        Clock.schedule_once(self._redraw, 0)

    @staticmethod
    def _parse_dt_local(value: str):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                return dt.astimezone()
            return dt.astimezone()
        except Exception:
            return None

    def _layout_events(self, items):
        # items: list of (start_min, end_min, ev)
        items.sort(key=lambda x: (x[0], x[1]))
        # Sweep line to group overlapping intervals
        groups = []
        current = []
        current_end = -1
        for s,e,ev in items:
            if s > current_end:
                if current:
                    groups.append(current)
                current = [(s,e,ev)]
                current_end = e
            else:
                current.append((s,e,ev))
                current_end = max(current_end, e)
        if current:
            groups.append(current)
        # For each group, assign columns greedily
        laid = []
        for group in groups:
            cols = []  # each col stores last end
            base_index = len(laid)
            for s,e,ev in sorted(group, key=lambda x: (x[0], x[1])):
                placed = False
                for ci,last_end in enumerate(cols):
                    if s >= last_end:
                        cols[ci] = e
                        laid.append((s,e,ev,ci,len(cols)))
                        placed = True
                        break
                if not placed:
                    cols.append(e)
                    ci = len(cols)-1
                    laid.append((s,e,ev,ci,len(cols)))
            # update total columns only for the entries added in this group
            total_cols = len(cols)
            for i in range(base_index, len(laid)):
                s,e,ev,ci,tc = laid[i]
                laid[i] = (s,e,ev,ci,total_cols)
        return laid

    def _redraw(self, *args):
        self.canvas.clear()
        # Clear previous child widgets (hour labels and events)
        for child in list(self.children):
            self.remove_widget(child)

        # Helper to map minutes since start-of-day to Y so that 00:00 is at the top
        def y_for_min(mins: int) -> float:
            return self.content_height - (mins * self.dp_per_min)

        with self.canvas:
            # Hour grid (top = start of day, bottom = end of day)
            Color(*self.hour_color)
            for h in range(25):
                y = y_for_min(h * 60)
                Line(points=[self.left_pad, y, self.width - self.right_pad, y], width=1)
            # Now line (if same day)
            now = datetime.now().astimezone()
            if now.date() == self.day_date.date():
                mins = now.hour * 60 + now.minute
                y = y_for_min(mins)
                Color(*NOW_LINE)
                Line(points=[self.left_pad, y, self.width - self.right_pad, y], width=1.2)

        # Hour labels as widgets
        for h in range(24):
            y = y_for_min(h * 60)
            lbl = Label(text=f"{h:02d}:00", color=TEXT_SUBTLE, size_hint=(None, None), size=(self.left_pad - dp(8), dp(16)))
            lbl.pos = (dp(4), y - dp(8))
            self.add_widget(lbl)

        # Prepare events for the selected day
        items = []
        day_start = self.day_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone()
        day_end = day_start + timedelta(days=1)
        for ev in self.events:
            s = self._parse_dt_local(ev.get("from"))
            e = self._parse_dt_local(ev.get("to")) or s
            if not s:
                continue
            # clip to day
            if e <= day_start or s >= day_end:
                continue
            s_clip = max(s, day_start)
            e_clip = min(e, day_end)
            s_min = int((s_clip - day_start).total_seconds() // 60)
            e_min = max(s_min + 5, int((e_clip - day_start).total_seconds() // 60))  # at least 5 minutes
            items.append((s_min, e_min, ev))

        laid = self._layout_events(items)
        for s_min, e_min, ev, col_idx, total_cols in laid:
            # Inverted vertical mapping: earlier at top, later at bottom
            top = y_for_min(s_min)
            bottom = y_for_min(e_min)
            width = self.width - self.left_pad - self.right_pad
            col_w = width / max(1, total_cols)
            x = self.left_pad + col_idx * col_w + dp(2)
            w = col_w - dp(4)
            y = bottom + dp(1)
            h = max(dp(18), top - bottom - dp(2))
            # Event block as a label with colored background rectangle
            box = Label(text=f"[b]{ev.get('title','(No title)')}[/b] ({ev.get('organizer','')})", markup=True, halign='left', valign='top', color=self.event_text_color)
            box.size_hint = (None, None)
            box.text_size = (w - dp(2), h - dp(2))
            box.size = (w, h)
            box.pos = (x, y)

            # canvas background linked to pos/size
            def _update_bg(widget, *a):
                box.canvas.before.clear()
                with box.canvas.before:
                    Color(*EVENT_BLOCK_BG_ALT)
                    Rectangle(pos=box.pos, size=box.size)
                    Color(*EVENT_BORDER_SHADOW)
                    Line(rectangle=(box.x, box.y, box.width, box.height), width=1)

            box.bind(pos=_update_bg, size=_update_bg)
            _update_bg(box)
            self.add_widget(box)


class DayScheduleModal(ModalView):
    def __init__(self, events:list, day_date:datetime, **kwargs):
        super().__init__(size_hint=(0.98, 0.98), auto_dismiss=True, background_color=BG_MODAL)
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        header = Label(text=day_date.strftime("%A, %d %B %Y"), size_hint_y=None, height=dp(30), color=TEXT_PRIMARY)
        root.add_widget(header)
        sc = ScrollView(size_hint=(1,1))
        timeline = DayScheduleView(events, day_date)
        sc.add_widget(timeline)
        root.add_widget(sc)
        self.add_widget(root)

        def scroll_to_10am(*args):
            # total height of timeline (24h * 60min * dp_per_min)
            total_height = timeline.content_height
            # height from top for 10:00 (10 * 60 * dp_per_min)
            y_10am = 10 * 60 * timeline.dp_per_min
            # scroll_y is relative: 1 = top, 0 = bottom
            scroll_y = 1 - (y_10am / total_height)
            sc.scroll_y = max(0, min(1, scroll_y))

        # Wait for the next frame so ScrollView has the proper size
        Clock.schedule_once(scroll_to_10am, 0.2)


class DashboardApp(MDApp):
    _wakelock = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_url = BASE_URL + "/stats"
        self.gauges = {}
        self.events_panel = EventsPanel()
        self._last_events = []
        self._calendar_modal = None

    def open_calendar_modal(self, year:int, month:int):
        def on_pick(dt: datetime):
            try:
                self._on_date_selected(dt)
            except Exception:
                pass
        try:
            if self._calendar_modal:
                self._calendar_modal.dismiss()
        except Exception:
            pass
        self._calendar_modal = BigCalendarModal(year, month, on_pick)
        self._calendar_modal.open()

    def _load_events_fallback(self) -> list:
        return []

    def _events_for_day(self, day_date: datetime) -> list:
        # Prefer the latest polled events; fallback to bundled resp.json
        events = self._last_events or self._load_events_fallback()
        if not events:
            return []
        # Filter by the selected local day
        day_start = day_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone()
        day_end = day_start + timedelta(days=1)
        def parse_local(v):
            try:
                dt = datetime.fromisoformat(v)
                return dt.astimezone() if dt else None
            except Exception:
                return None
        filtered = []
        for ev in events:
            s = parse_local(ev.get("from"))
            e = parse_local(ev.get("to")) or s
            if not s:
                continue
            if e > day_start and s < day_end:
                filtered.append(ev)
        return filtered

    def fetch_events_for_date(self, day_date: datetime):
        date_str = day_date.strftime("%Y-%m-%d")
        url = f"{BASE_URL}/events?date={date_str}"

        def _ok(req, result):
            evs = []
            try:
                if isinstance(result, dict):
                    evs = result.get("events", []) or result.get("data", [])
                elif isinstance(result, list):
                    evs = result
            except Exception:
                evs = []
            if not evs:
                # fallback to locally known events for the day
                evs = self._events_for_day(day_date)
            DayScheduleModal(evs, day_date).open()

        def _fail(req, result):
            evs = self._events_for_day(day_date)
            DayScheduleModal(evs, day_date).open()

        try:
            UrlRequest(url, on_success=_ok, on_error=_fail, on_failure=_fail, timeout=3)
        except Exception:
            _fail(None, None)

    def _on_date_selected(self, dt: datetime):
        # Try fetching from API, fallback to the local sample if needed
        self.fetch_events_for_date(dt)

    @staticmethod
    def _android_keep_awake(apply: bool):
        try:
            if core_platform != "android" or autoclass is None:
                return
            python_activity = autoclass('org.kivy.android.PythonActivity')
            activity = python_activity.mActivity
            windowmanager_layout_params = autoclass('android.view.WindowManager$LayoutParams')
            window = activity.getWindow()
            if apply:
                window.addFlags(windowmanager_layout_params.FLAG_KEEP_SCREEN_ON)
                # Some OEMs require these to avoid dimming/lock when app shows
                try:
                    window.addFlags(windowmanager_layout_params.FLAG_TURN_SCREEN_ON)
                    window.addFlags(windowmanager_layout_params.FLAG_SHOW_WHEN_LOCKED)
                except Exception:
                    pass
            else:
                window.clearFlags(windowmanager_layout_params.FLAG_KEEP_SCREEN_ON)
                try:
                    window.clearFlags(windowmanager_layout_params.FLAG_TURN_SCREEN_ON)
                    window.clearFlags(windowmanager_layout_params.FLAG_SHOW_WHEN_LOCKED)
                except Exception:
                    pass
        except Exception:
            # Best-effort only
            pass

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"
        # Try multiple strategies to keep the screen awake
        Window.keep_screen_on = True
        try:
            Window.allow_screensaver = False
        except Exception:
            pass
        root = Builder.load_string(KV)
        self._last_events = []

        # Top row: four gauge cards
        def gauge_card(_title):
            _card = MDCard(orientation="vertical", padding=dp(8), radius=[16], elevation=6)
            if _title == "Battery":
                gauge = Gauge(label=_title, reverse_color_logic=True)
            else:
                gauge = Gauge(label=_title)
            _card.add_widget(gauge)
            return _card, gauge

        for title, key in [("CPU", "cpu"), ("Memory", "mem"), ("Network", "net"), ("Battery", "power")]:
            card, g = gauge_card(title)
            self.gauges[key] = g
            root.ids.top_row.add_widget(card)

        # Bottom row: The first card contains both clocks, middle card has calendar, right card has events
        def card_with(widget):
            _card = MDCard(orientation="vertical", padding=dp(12), radius=[16], elevation=6)
            _card.add_widget(widget)
            return _card

        # First card: both clocks stacked
        local_clock = DigitalClock(tz="local", title="New Delhi")
        utc_clock = DigitalClock(tz="Europe/Berlin", title="Munich")

        clocks_box = BoxLayout(orientation="vertical", spacing=dp(10), padding=(0, 0, 0, 0))
        clocks_box.add_widget(local_clock)
        clocks_box.add_widget(utc_clock)
        root.ids.bottom_row.add_widget(card_with(clocks_box))

        # Middle card: calendar
        calendar_widget = MonthCalendar()
        root.ids.bottom_row.add_widget(card_with(calendar_widget))

        # Right card: events
        root.ids.bottom_row.add_widget(card_with(self.events_panel))

        # Poll stats
        Clock.schedule_interval(self.update_stats, 2)
        return root

    def on_start(self):
        # Additional keep-awake strategies when the app becomes active
        try:
            if plyer_keepawake is not None:
                plyer_keepawake.on()
        except Exception:
            pass
        # On Android, also add window flags to be extra sure
        self._android_keep_awake(apply=True)

    def on_stop(self):
        # Release keep-awake strategies on app stop
        try:
            if plyer_keepawake is not None:
                plyer_keepawake.off()
        except Exception:
            pass
        self._android_keep_awake(apply=False)

    def on_pause(self):
        # App is going to background; release keep-awake
        try:
            if plyer_keepawake is not None:
                plyer_keepawake.off()
        except Exception:
            pass
        self._android_keep_awake(apply=False)
        return True

    def on_resume(self):
        # App returned to foreground; re-apply keep-awake
        try:
            if plyer_keepawake is not None:
                plyer_keepawake.on()
        except Exception:
            pass
        self._android_keep_awake(apply=True)

    def update_stats(self, dt):
        def _ok(req, result):
            self.show_data(result or {})

        def _fail(req, result):
            # Keep previous values on failure; you may log or set 0 s
            pass

        try:
            UrlRequest(self.api_url, on_success=_ok, on_error=_fail, on_failure=_fail, timeout=2)
        except Exception:
            pass

    def show_data(self, result):
        """
        Update all gauges with smooth animation and safe defaults.
        """

        def safe_float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        # CPU
        cpu = self.gauges.get("cpu")
        if cpu:
            cpu.animate_to(safe_float(result.get("cpu", 0)))

        # Memory
        mem = self.gauges.get("mem")
        if mem:
            mem.animate_to(safe_float(result.get("mem", 0)))

        # Network (can come as 'net', 'network', or 'disk')
        net = self.gauges.get("net")
        if net:
            net_val = result.get("net", result.get("network", result.get("disk", 0)))
            net.animate_to(safe_float(net_val))

        # Power / Battery
        power = self.gauges.get("power")
        if power:
            power_val = result.get("battery", result.get("power", 0))
            power.animate_to(safe_float(power_val))

        # Events list
        try:
            events = result.get("events", [])
        except Exception:
            events = []
        self._last_events = events or self._last_events
        if hasattr(self, "events_panel") and self.events_panel:
            try:
                self.events_panel.update_events(self._last_events)
            except Exception:
                pass


if __name__ == "__main__":
    DashboardApp().run()
