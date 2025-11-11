from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from colors import CLOCK_LOCAL_COLOR, CLOCK_TZ_COLOR


class DigitalClock(BoxLayout):
    def __init__(self, tz="local", title="Clock", **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(6), **kwargs)
        self.tz = tz
        color = CLOCK_LOCAL_COLOR if tz == "local" else CLOCK_TZ_COLOR
        self.title = Label(text=title, color=color, font_size="16sp", size_hint_y=None, height=dp(18))
        self.time_lbl = Label(text="--:--:--", markup=True, color=color, font_size="50sp")
        self.add_widget(self.title)
        self.add_widget(self.time_lbl)
        self._last_sec = None
        Clock.schedule_interval(self._update_time, 1 / 30)
        self._update_time(0)

    def _get_now(self):
        if self.tz == "local":
            return datetime.now().astimezone()
        try:
            return datetime.now(ZoneInfo(self.tz)).astimezone()
        except ZoneInfoNotFoundError:
            return datetime.now().astimezone()

    def _update_time(self, dt):
        now = self._get_now()
        sec = now.second
        if getattr(self, "_last_sec", None) != sec:
            self._last_sec = sec
            self.time_lbl.text = now.strftime("%H:%M:%S")
