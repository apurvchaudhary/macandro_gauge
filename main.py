import calendar as pycalendar
from datetime import datetime
from importlib import import_module
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
from kivy.utils import platform as core_platform
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.list import MDList, TwoLineListItem

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


class DigitalClock(BoxLayout):
    """A sleek digital clock with timezone support."""

    def __init__(self, tz: str = "local", title: str = "Clock", **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(6), **kwargs)
        self.tz = tz
        if tz == "local":
            color = get_color_from_hex("#5F85F5")
        else:
            color = get_color_from_hex("5FF580")
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
    """A minimal monthly calendar that highlights today and supports swiping."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(6), **kwargs)
        self.title = Label(
            text="Calendar", color=(0.8, 0.85, 0.9, 1), font_size="18sp", size_hint_y=None, height=dp(24)
        )
        self.header = Label(text="", font_size="20sp", color=(1, 1, 1, 1), size_hint_y=None, height=dp(28))
        self.grid = None
        # Track which month/year are displayed
        today = datetime.now()
        self.display_year = today.year
        self.display_month = today.month
        # Track touch for swipe
        self._touch_start = None
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
            self.grid.add_widget(Label(text=wd, color=(0.7, 0.8, 0.95, 1)))
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
                    col = (0.2, 1, 0.9, 1) if is_today else (0.9, 0.95, 1, 1)
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
        self._touch_start = None
        if handled:
            return True
        return super().on_touch_up(touch)


class EventsPanel(BoxLayout):
    """Scrollable list of events from the API; highlights the next event."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(6), **kwargs)
        self.title = Label(text="Events", color=(0.8, 0.85, 0.9, 1), font_size="16sp", size_hint_y=None, height=dp(24))
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

    def update_events(self, events: list):
        # Clear the current list
        self.list.clear_widgets()
        if not events:
            self.list.add_widget(TwoLineListItem(text="No upcoming events", secondary_text=""))
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
            self.list.add_widget(TwoLineListItem(text="No upcoming events", secondary_text=""))
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
                    li.text_color = get_color_from_hex("#2FF3E0")
                except Exception:
                    pass
            self.list.add_widget(li)


class DashboardApp(MDApp):
    _wakelock = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_url = "http://192.168.1.30:8001/stats"
        self.gauges = {}
        self.events_panel = EventsPanel()

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
        if hasattr(self, "events_panel") and self.events_panel:
            try:
                self.events_panel.update_events(events)
            except Exception:
                pass


if __name__ == "__main__":
    DashboardApp().run()
