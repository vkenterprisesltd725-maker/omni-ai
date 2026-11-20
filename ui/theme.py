"""
OmniAI Studio - Minimalist Monochrome Design Theme
Clean, high-legibility white, grey, and black palette inspired by Linear, Notion, and Apple.
Engineered by VIKA-BUILDS.
"""

"""
OmniAI Studio - Minimalist Monochrome Design Theme
Clean, high-legibility dual-mode (Light / Dark) palette inspired by Claude, Linear, and Notion.
Engineered by VIKA-BUILDS.
"""

# Minimalist Canvas & Structure (Light, Dark)
COLOR_CANVAS = ("#FAFAFA", "#0D0D0F")            # Off-white in light, deep obsidian in dark
COLOR_SIDEBAR = ("#FFFFFF", "#141417")           # Crisp white in light, deep charcoal in dark
COLOR_CARD = ("#FFFFFF", "#18181C")              # Pure white cards in light, elevated cards in dark
COLOR_CARD_ALT = ("#F4F5F7", "#1E1E24")          # Elevated container / alternate card
COLOR_CARD_HOVER = ("#F3F4F6", "#26262C")        # Subtle hover state
COLOR_BORDER = ("#E5E7EB", "#2E2E34")            # 1px hairline border
COLOR_BORDER_GLOW = ("#18181B", "#FAFAFA")       # Focused border
COLOR_INPUT = ("#FFFFFF", "#18181C")             # Input fields

# Monochromatic Accents (Light, Dark)
COLOR_ACCENT = ("#18181B", "#FAFAFA")            # Modern primary action
COLOR_ACCENT_HOVER = ("#3F3F46", "#E4E4E7")      # Hover state for primary buttons
COLOR_SECONDARY = ("#F4F4F5", "#222227")         # Secondary action button fill
COLOR_SECONDARY_HOVER = ("#E4E4E7", "#2E2E35")   # Secondary action hover
COLOR_INDIGO = ("#4F46E5", "#6366F1")            # Subtle computational accent

# Functional Status Indicators (Light, Dark)
COLOR_SUCCESS = ("#059669", "#10B981")           # Clean emerald (200 OK / Ready)
COLOR_WARNING = ("#D97706", "#F59E0B")           # Clean amber (Cooldown / Rate limits)
COLOR_ERROR = ("#DC2626", "#EF4444")             # Clean red (Errors)

# Typography & Text (Light, Dark)
COLOR_TEXT_MAIN = ("#111827", "#F9FAFB")         # Primary typography
COLOR_TEXT_MUTED = ("#4B5563", "#A1A1AA")        # Secondary typography
COLOR_TEXT_DIM = ("#9CA3AF", "#71717A")          # Subtle captions and timestamps

# Chat Bubbles (Linear / Notion Style)
COLOR_USER_BUBBLE = ("#F3F4F6", "#222227")       # Soft card for user message
COLOR_USER_BUBBLE_BORDER = ("#E5E7EB", "#2E2E34")
COLOR_ASSISTANT_BUBBLE = ("#FFFFFF", "#18181C")  # Card for assistant message
COLOR_ASSISTANT_BUBBLE_BORDER = ("#E5E7EB", "#2E2E34")

# Backward compatibility aliases
COLOR_CARD_DARK = COLOR_CARD
COLOR_BG_DARK = COLOR_CANVAS
COLOR_SIDEBAR_DARK = COLOR_SIDEBAR
COLOR_INPUT_DARK = COLOR_INPUT

# Typography Scale
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_HEADING = ("Segoe UI", 13, "bold")
FONT_SUBHEADING = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_BODY_BOLD = ("Segoe UI", 10, "bold")
FONT_CODE = ("Consolas", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BADGE = ("Segoe UI", 9, "bold")
FONT_METRIC = ("Segoe UI", 16, "bold")
