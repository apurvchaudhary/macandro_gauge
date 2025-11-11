import calendar as pycalendar
from datetime import datetime

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from colors import (
    TEXT_PRIMARY,
    TEXT_SUBTLE,
    CAL_WEEKDAY_HDR,
    CAL_DAY_NORMAL,
    CAL_DAY_NORMAL_ALT,
    CAL_DAY_TODAY,
    BG_MODAL,
)


class DayCell(ButtonBehavior, Label):
    def __init__(self, day: int, is_today: bool, on_pick, **kwargs):
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
    def __init__(self, year: int, month: int, on_select, **kwargs):
        super().__init__(size_hint=(0.95, 0.95), auto_dismiss=True, background_color=BG_MODAL, **kwargs)
        self.on_select = on_select
        self.year = year
        self.month = month
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        header = Label(text=f"{pycalendar.month_name[month]} {year}", font_size="22sp", color=TEXT_PRIMARY, size_hint_y=None, height=dp(30))
        root.add_widget(header)
        grid = GridLayout(cols=7, rows=7, spacing=dp(6))
        for wd in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            grid.add_widget(Label(text=wd, color=CAL_WEEKDAY_HDR))
        cal = pycalendar.Calendar(firstweekday=0)
        today = datetime.now()
        def pick(_day):
            if callable(self.on_select):
                self.dismiss()
                self.on_select(datetime(year, month, _day))
        for week in cal.monthdayscalendar(year, month):
            for day in week:
                if day == 0:
                    grid.add_widget(Label(text=""))
                else:
                    is_today = (year==today.year and month==today.month and day==today.day)
                    grid.add_widget(DayCell(day, is_today, pick))
        root.add_widget(grid)
        self.add_widget(root)


class MonthCalendar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(6), **kwargs)
        self.title = Label(text="Calendar", color=TEXT_SUBTLE, font_size="18sp", size_hint_y=None, height=dp(24))
        self.header = Label(text="", font_size="20sp", color=TEXT_PRIMARY, size_hint_y=None, height=dp(28))
        self.grid = None
        today = datetime.now()
        self.display_year = today.year
        self.display_month = today.month
        self._touch_start = None
        self._last_day_shown = today.day
        self.add_widget(self.title)
        self.add_widget(self.header)
        self._build()
        Clock.schedule_interval(self._maybe_refresh, 30)

    def _set_month(self, year: int, month: int):
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
        if self.grid is not None:
            self.remove_widget(self.grid)
            self.grid = None
        year, month = self.display_year, self.display_month
        self.header.text = pycalendar.month_name[month] + f" {year}"
        self.grid = GridLayout(cols=7, rows=7, spacing=dp(4))
        for wd in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            self.grid.add_widget(Label(text=wd, color=CAL_WEEKDAY_HDR))
        cal = pycalendar.Calendar(firstweekday=0)
        today = datetime.now()
        for week in cal.monthdayscalendar(year, month):
            for day in week:
                if day == 0:
                    self.grid.add_widget(Label(text=""))
                else:
                    is_today = (year == today.year and month == today.month and day == today.day)
                    txt = f"[b]{day}[/b]" if is_today else str(day)
                    col = CAL_DAY_TODAY if is_today else CAL_DAY_NORMAL
                    self.grid.add_widget(Label(text=txt, markup=True, color=col))
        self.add_widget(self.grid)

    def _maybe_refresh(self, dt):
        now = datetime.now()
        if self.display_year == now.year and self.display_month == now.month:
            if getattr(self, "_last_day_shown", None) != now.day:
                self._last_day_shown = now.day
                self._build()

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
                    self._shift_month(+1)
                else:
                    self._shift_month(-1)
                handled = True
            else:
                try:
                    from kivy.app import App
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
