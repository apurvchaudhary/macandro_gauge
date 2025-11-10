from kivy.utils import get_color_from_hex

# Shared color constants (RGBA lists/tuples) for reuse across the app.
# Semantic names help keep the UI consistent.

# Text colors
TEXT_PRIMARY = (1, 1, 1, 1)
TEXT_SUBTLE = (0.8, 0.85, 0.9, 1)
TEXT_MUTED = (0.7, 0.75, 0.8, 1)
TEXT_DARK = (0.05, 0.08, 0.1, 1)

# Calendar colors
CAL_WEEKDAY_HDR = (0.7, 0.8, 0.95, 1)
CAL_DAY_NORMAL = (0.9, 0.95, 1, 1)
CAL_DAY_NORMAL_ALT = (0.95, 0.98, 1, 1)
CAL_DAY_TODAY = (0.2, 1, 0.9, 1)

# Modal / surfaces
BG_MODAL = get_color_from_hex("#4CC9F0")
BG_HALO = (0.07, 0.07, 0.09, 1)

# Schedule / timeline
SCHEDULE_HOUR_LINE = (0.3, 0.35, 0.4, 1)
EVENT_BLOCK_BG = get_color_from_hex("#4CC9F0")
EVENT_BLOCK_BG_ALT = get_color_from_hex("#21B0F1")
EVENT_BLOCK_TEXT = TEXT_DARK
NOW_LINE = (1, 0, 0, 1)
EVENT_BORDER_SHADOW = (0, 0, 0, 0.25)

# Digital clock accents
CLOCK_LOCAL_COLOR = get_color_from_hex("#5F85F5")
CLOCK_TZ_COLOR = get_color_from_hex("#5FF580")

# Gauge component colors
GAUGE_TRACK = [0.15, 0.15, 0.18, 1]
GAUGE_PROGRESS_DEFAULT = [0, 0.51, 0, 1]
GAUGE_ACCENT = [1, 0.3, 0.3, 1]
GAUGE_TICKS = (0.7, 0.75, 0.8, 1)

# Gauge progresses dynamic colors
PROGRESS_GOOD = get_color_from_hex("#2B8A2F")
PROGRESS_WARN = get_color_from_hex("#FFBE3D")
PROGRESS_BAD = get_color_from_hex("#B3280C")

# Events panel highlight
EVENT_HIGHLIGHT = get_color_from_hex("#2FF3E0")
