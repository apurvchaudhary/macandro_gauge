import threading
import time
import traceback
from datetime import timedelta
from importlib import import_module

from kivy.config import Config

Config.set('graphics', 'maxfps', '60')

from kivy.lang import Builder
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.app import App

try:
    from kivymd.app import MDApp
    from kivymd.uix.card import MDCard
except Exception:
    MDApp = App
    from kivy.uix.boxlayout import BoxLayout as MDCard

from widgets import DigitalClock, MonthCalendar, EventsPanel, DayScheduleModal
from gauge import Gauge

# optional keep-awake via plyer
plyer_keepawake = None
try:
    plyer = import_module("plyer")
    if hasattr(plyer, "keepawake"):
        plyer_keepawake = plyer.keepawake
except Exception:
    plyer_keepawake = None

BASE_URL = "http://192.168.1.30:8001"

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


def parse_iso_to_local(value):
    if not value:
        return None
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        from datetime import datetime as _dt
        dt = _dt.fromisoformat(s)
    except Exception:
        try:
            from dateutil import parser
            dt = parser.isoparse(s)
        except Exception:
            return None
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.astimezone()
    return dt.astimezone()


class StatsFetcher(threading.Thread):
    def __init__(self, url, callback, interval=2.0):
        super().__init__(daemon=True)
        self.url = url
        self.callback = callback
        self.interval = interval
        self.running = True
        try:
            import requests
            self.requests = requests
        except Exception:
            self.requests = None

    def run(self):
        while self.running:
            start = time.time()
            data = {}
            try:
                if self.requests:
                    r = self.requests.get(self.url, timeout=2)
                    data = r.json() if r is not None else {}
            except Exception:
                data = {}
            try:
                Clock.schedule_once(lambda *_: self.callback(data))
            except Exception:
                pass
            elapsed = time.time() - start
            time.sleep(max(0, self.interval - elapsed))

    def stop(self):
        self.running = False


class DashboardApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gauges = {}
        self.events_panel = EventsPanel()
        self._last_events = []
        self._fetcher = None
        self.api_url = f"{BASE_URL}/stats"

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"
        Window.keep_screen_on = True
        try:
            Window.allow_screensaver = False
        except Exception:
            pass

        root = Builder.load_string(KV)

        def gauge_card(title, key, reverse=False):
            card = MDCard(orientation="vertical", padding=dp(8), radius=[16], elevation=6)
            g = Gauge(label=title, reverse_color_logic=reverse)
            card.add_widget(g)
            self.gauges[key] = g
            root.ids.top_row.add_widget(card)

        gauge_card("CPU", "cpu")
        gauge_card("Memory", "mem")
        gauge_card("Network", "net")
        gauge_card("Battery", "power", reverse=True)

        from kivy.uix.boxlayout import BoxLayout as KBox
        clocks_box = KBox(orientation="vertical", spacing=dp(10))
        clocks_box.add_widget(DigitalClock(tz="local", title="New Delhi"))
        clocks_box.add_widget(DigitalClock(tz="Europe/Berlin", title="Munich"))
        ccard = MDCard(orientation="vertical", padding=dp(12), radius=[16], elevation=6)
        ccard.add_widget(clocks_box)
        root.ids.bottom_row.add_widget(ccard)

        cal_card = MDCard(orientation="vertical", padding=dp(12), radius=[16], elevation=6)
        cal_card.add_widget(MonthCalendar())
        root.ids.bottom_row.add_widget(cal_card)

        ev_card = MDCard(orientation="vertical", padding=dp(12), radius=[16], elevation=6)
        ev_card.add_widget(self.events_panel)
        root.ids.bottom_row.add_widget(ev_card)
        self._start_fetcher()
        return root

    def _start_fetcher(self):
        if self._fetcher is None:
            self._fetcher = StatsFetcher(self.api_url, self.show_data)
            self._fetcher.start()

    def on_start(self):
        try:
            if plyer_keepawake is not None:
                plyer_keepawake.on()
        except Exception:
            pass

    def on_stop(self):
        try:
            if plyer_keepawake is not None:
                plyer_keepawake.off()
        except Exception:
            pass
        if self._fetcher:
            self._fetcher.stop()

    def open_calendar_modal(self, year: int, month: int):
        from widgets.calendar import BigCalendarModal
        def pick(dt):
            try:
                self.fetch_events_for_date(dt)
            except Exception:
                traceback.print_exc()
        try:
            modal = BigCalendarModal(year, month, pick)
            modal.open()
        except Exception:
            traceback.print_exc()

    def fetch_events_for_date(self, day_date):
        # background fetch for events; simple thread wrapper
        def worker():
            url = f"{BASE_URL}/events?date={day_date.strftime('%Y-%m-%d')}"
            evs = []
            try:
                import requests
                r = requests.get(url, timeout=3)
                result = r.json()
                if isinstance(result, dict):
                    evs = result.get("events", []) or result.get("data", [])
                elif isinstance(result, list):
                    evs = result
            except Exception:
                evs = self._events_for_day(day_date)
            Clock.schedule_once(lambda *_: DayScheduleModal(evs, day_date).open())
        threading.Thread(target=worker, daemon=True).start()

    def _events_for_day(self, day_date):
        events = self._last_events or []
        if not events:
            return []
        day_start = day_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone()
        day_end = day_start + timedelta(days=1)
        filtered = []
        for ev in events:
            s = parse_iso_to_local(ev.get("from"))
            e = parse_iso_to_local(ev.get("to")) or s
            if not s:
                continue
            if e > day_start and s < day_end:
                filtered.append(ev)
        return filtered

    def show_data(self, result):
        def safe_float(v):
            try:
                return float(v)
            except Exception:
                return 0.0

        cpu = safe_float(result.get("cpu", 0))
        mem = safe_float(result.get("mem", 0))
        net = safe_float(result.get("net", result.get("network", result.get("disk", 0))))
        power = safe_float(result.get("battery", result.get("power", 0)))
        events = result.get("events", []) if isinstance(result, dict) else []

        stagger = 0.08
        Clock.schedule_once(lambda *_: self.gauges.get("cpu") and self.gauges["cpu"].animate_to(cpu), 0 * stagger)
        Clock.schedule_once(lambda *_: self.gauges.get("mem") and self.gauges["mem"].animate_to(mem), 1 * stagger)
        Clock.schedule_once(lambda *_: self.gauges.get("net") and self.gauges["net"].animate_to(net), 2 * stagger)
        Clock.schedule_once(lambda *_: self.gauges.get("power") and self.gauges["power"].animate_to(power), 3 * stagger)

        try:
            if events != self._last_events:
                self._last_events = events
                self.events_panel.update_events(events)
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    DashboardApp().run()
