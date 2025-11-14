from datetime import datetime, timedelta

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivymd.uix.list import (
    MDListItem,
    MDListItemHeadlineText,
    MDListItemSupportingText,
)

from colors import TEXT_SUBTLE, EVENT_HIGHLIGHT

CLEAR_EVENT_START_BUFFER_MINUTES = 2


class EventListItem(MDListItem):
    """Modern two-line event list item for KivyMD 2.x."""

    def __init__(self, title: str, subtitle: str = "", highlight=False, **kwargs):
        super().__init__(**kwargs)

        self.ripple_effect = False
        self.radius = [16]
        self.md_bg_color = (0, 0, 0, 0)  # transparent by default

        # Colors
        title_color = EVENT_HIGHLIGHT if highlight else (1, 1, 1, 1)
        subtitle_color = TEXT_SUBTLE

        headline = MDListItemHeadlineText(
            text=title,
            font_style="Label",
            theme_text_color="Custom",
            text_color=title_color,
            role="medium",
            shorten=True,
        )

        supporting = MDListItemSupportingText(
            text=subtitle,
            font_style="Body",
            theme_text_color="Custom",
            text_color=subtitle_color,
        )

        # Add the texts as children
        self.add_widget(headline)
        self.add_widget(supporting)


# ---------- Helper to parse ISO timestamps ----------
def parse_iso_to_local(value):
    if not value:
        return None
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            from dateutil import parser
            dt = parser.isoparse(s)
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone()


# ---------- Main Events Panel ----------
class EventsPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(4), **kwargs)

        self.title = Label(
            text="Today",
            color=TEXT_SUBTLE,
            font_size="16sp",
            size_hint_y=None,
            height=dp(12),
        )
        self.add_widget(self.title)

        self.scroll = ScrollView(size_hint=(1, 1))
        self.list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
            padding=(0, dp(4))
        )
        self.list.bind(minimum_height=self.list.setter("height"))
        self.scroll.add_widget(self.list)
        self.add_widget(self.scroll)

    @staticmethod
    def _format_slot(start: datetime, end: datetime, location: str | None):
        """Format time slot string like 'Today 16:30-18:00 · Room'."""
        if not start:
            return ""
        local_now = datetime.now().astimezone()
        same_day = start.date() == local_now.date()
        time_part = start.strftime("%H:%M")
        end_part = end.strftime("%H:%M") if end else ""
        date_part = "Today" if same_day else start.strftime("%a, %d %b")
        loc_part = f" · {location}" if location else ""
        if end_part:
            return f"{date_part} {time_part}-{end_part}{loc_part}"
        return f"{date_part} {time_part}{loc_part}"

    def __clear_event_list(self):
        self.list.clear_widgets()

    @staticmethod
    def get_validated_events(events: list):
        validated_events = []
        local_now = datetime.now().astimezone()
        for event in events:
            start = parse_iso_to_local(event.get("from"))
            end = parse_iso_to_local(event.get("to"))
            if start is None and end is None:
                continue
            sort_key = start or end or local_now
            if start and start <= (local_now - timedelta(minutes=CLEAR_EVENT_START_BUFFER_MINUTES)):
                continue
            validated_events.append((sort_key, event, start, end))
        return validated_events

    def update_events(self, validated_events: list[tuple]):
        self.__clear_event_list()
        if not validated_events:
            return
        validated_events.sort(key=lambda x: x[0])
        for idx, (_, ev, start, end) in enumerate(validated_events):
            title = ev.get("title") or "(No title)"
            subtitle = self._format_slot(start, end, ev.get("location"))
            li = EventListItem(title=title, subtitle=subtitle, highlight=(idx == 0))
            self.list.add_widget(li)
