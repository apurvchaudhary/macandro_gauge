from kivy.animation import Animation
from kivy.graphics import Color, Line, Ellipse, PushMatrix, PopMatrix, Rotate, Translate
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty, ListProperty, BooleanProperty
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from math import radians, sin, cos


class Gauge(Widget):
    """
    A sleek, responsive radial gauge for 0–100 values with a wow look.

    - Draws a 240° arc (from -210° to +30°) with a background track and a
      colorful progress track.
    - Shows tick marks every 10 and bold ticks every 20.
    - Center shows value and label.
    """

    value = NumericProperty(0)
    label = StringProperty("")
    reverse_color_logic = BooleanProperty(False)
    # Colors: [r, g, b, a]
    track_color = ListProperty([0.15, 0.15, 0.18, 1])
    progress_color = ListProperty([0, 0.51, 0, 1])
    accent_color = ListProperty([1, 0.3, 0.3, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value_label = Label(text="0%", color=(1, 1, 1, 1))
        self.title_label = Label(text=self.label, color=(0.8, 0.85, 0.9, 1))
        self.add_widget(self.value_label)
        self.add_widget(self.title_label)
        self.bind(pos=self._update, size=self._update, value=self._update, label=self._update)

    def __animate_color(self, value):
        """Animate progress color based on the current value."""
        if not self.reverse_color_logic:
            # cpu, mem
            if value < 50:
                # below 50%
                target_color = get_color_from_hex("#2B8A2F")
            elif value < 80:
                # 50-80%
                target_color = get_color_from_hex("#FFBE3D")
            else:
                # above 80%
                target_color = get_color_from_hex("#B3280C")
        else:
            # battery etc
            if value < 15:
                # below 15%
                target_color = get_color_from_hex("#B3280C")
            else:
                # above 15%
                target_color = get_color_from_hex("#2B8A2F")
        Animation.cancel_all(self, "progress_color")
        Animation(progress_color=target_color, duration=0.5, t="in_out_cubic").start(self)

    def animate_to(self, new_value, duration=0.5):
        """Smoothly animate the needle and fill color toward a new value."""
        Animation.cancel_all(self)
        anim = Animation(value=new_value, duration=duration, t="out_quad")
        anim.start(self)
        self.__animate_color(new_value)

    @property
    def _radius(self):
        # Keep it square within widget bounds
        return min(self.width, self.height) * 0.48

    @staticmethod
    def _map(value, a1, a2, b1, b2):
        # linear map clamped
        v = max(min(value, a2), a1)
        return b1 + (b2 - b1) * ((v - a1) / (a2 - a1) if a2 != a1 else 0)

    def _update(self, *args):
        self.canvas.before.clear()

        # Angles for the arc
        start_angle = -210
        end_angle = 30
        span = end_angle - start_angle  # 240°
        val_angle = start_angle + (span * max(0.0, min(1.0, self.value / 100.0)))

        cx, cy = self.center
        r = self._radius
        track_width = max(2.0, self.width * 0.03)
        progress_width = max(2.0, self.width * 0.04)

        with self.canvas.before:
            # subtle outer halo
            Color(0.07, 0.07, 0.09, 1)
            Ellipse(pos=(cx - r - dp(10), cy - r - dp(10)), size=(2 * (r + dp(10)), 2 * (r + dp(10))))

            # background track
            Color(*self.track_color)
            Line(circle=(cx, cy, r, start_angle, end_angle), width=track_width, cap="round")

            # progress track (gradient-like with two passes)
            Color(*self.progress_color)
            Line(circle=(cx, cy, r, start_angle, val_angle), width=progress_width, cap="round")

            # ticks
            Color(0.7, 0.75, 0.8, 1)
            for i in range(0, 101, 10):
                ang = radians(start_angle + (span * (i / 100.0)))
                outer = r + dp(2)
                inner = outer - (dp(10) if i % 20 == 0 else dp(6))
                x1 = cx + outer * cos(ang)
                y1 = cy + outer * sin(ang)
                x2 = cx + inner * cos(ang)
                y2 = cy + inner * sin(ang)
                Line(points=[x1, y1, x2, y2], width=1)

            # needle
            Color(*self.accent_color)
            PushMatrix()
            Translate(cx, cy)
            Rotate(angle=val_angle)
            Line(points=[0, 0, r * 0.85, 0], width=dp(2))
            PopMatrix()

        # Center labels
        self.value_label.text = f"{int(self.value)}%"
        self.title_label.text = self.label
        # Positioning
        self.value_label.center_x = cx
        self.value_label.center_y = cy + r * 0.15
        self.value_label.font_size = max(dp(12), self.width * 0.09)
        self.title_label.center_x = cx
        self.title_label.center_y = cy - r * 0.35
        self.title_label.font_size = max(dp(10), self.width * 0.06)
