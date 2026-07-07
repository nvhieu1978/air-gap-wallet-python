# GUI Styles and Theme Colors (Catppuccin Mocha Theme)

# Colors
BG_MAIN = "#1e1e2e"          # Dark base background
BG_SIDEBAR = "#11111b"       # Darker sidebar background
BG_CARD = "#252538"          # Slightly lighter card background
BG_INPUT = "#313244"         # Input background
BG_INPUT_ACTIVE = "#45475a"  # Active input/button hover background
BORDER_COLOR = "#45475a"     # Border line color

# Text Colors
TXT_PRIMARY = "#cdd6f4"      # Soft white text
TXT_SECONDARY = "#a6adc8"    # Subtext / description text
TXT_MUTED = "#6c7086"        # Disabled/muted text

# Accent Colors
COLOR_PRIMARY = "#cba6f7"    # Mauve (accent/buttons)
COLOR_SUCCESS = "#a6e3a1"    # Green (success states, balance)
COLOR_WARNING = "#f9e2af"    # Yellow (warnings, info)
COLOR_DANGER = "#f38ba8"     # Red (errors, danger operations)
COLOR_INFO = "#89b4fa"       # Blue (general status, link)

# Fonts
FONT_FAMILY = "sans-serif" # Fallback list, Tkinter matches automatically

FONT_TITLE = ("Helvetica", 18, "bold")
FONT_SUBTITLE = ("Helvetica", 14, "bold")
FONT_HEADER = ("Helvetica", 12, "bold")
FONT_BODY = ("Helvetica", 10)
FONT_BODY_BOLD = ("Helvetica", 10, "bold")
FONT_CODE = ("Courier", 9)
FONT_CODE_BOLD = ("Courier", 9, "bold")

# Layout Padding
PAD_XS = 4
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24
PAD_XL = 32

def configure_ttk_styles(style):
    """Configure ttk Style mappings to match our custom dark mode theme."""
    # Configure general elements
    style.theme_use("clam")
    
    # Global settings
    style.configure(".",
        background=BG_MAIN,
        foreground=TXT_PRIMARY,
        fieldbackground=BG_INPUT,
        font=FONT_BODY,
        troughcolor=BG_INPUT,
        bordercolor=BORDER_COLOR
    )
    
    # Frames
    style.configure("TFrame", background=BG_MAIN)
    style.configure("Card.TFrame", background=BG_CARD, relief="flat", borderwidth=0)
    style.configure("Sidebar.TFrame", background=BG_SIDEBAR)
    
    # Labels
    style.configure("TLabel", background=BG_MAIN, foreground=TXT_PRIMARY)
    style.configure("Sub.TLabel", background=BG_MAIN, foreground=TXT_SECONDARY)
    style.configure("Card.TLabel", background=BG_CARD, foreground=TXT_PRIMARY)
    style.configure("CardSub.TLabel", background=BG_CARD, foreground=TXT_SECONDARY)
    style.configure("Sidebar.TLabel", background=BG_SIDEBAR, foreground=TXT_SECONDARY)
    
    # Buttons
    style.configure("TButton",
        background=BG_INPUT,
        foreground=TXT_PRIMARY,
        bordercolor=BORDER_COLOR,
        focuscolor=COLOR_PRIMARY,
        relief="flat",
        padding=(PAD_MD, PAD_SM)
    )
    style.map("TButton",
        background=[("active", BG_INPUT_ACTIVE), ("pressed", BG_CARD)],
        foreground=[("active", TXT_PRIMARY)]
    )
    
    # Primary Accent Button
    style.configure("Primary.TButton",
        background=COLOR_PRIMARY,
        foreground=BG_MAIN,
        bordercolor=COLOR_PRIMARY,
        padding=(PAD_MD, PAD_SM)
    )
    style.map("Primary.TButton",
        background=[("active", "#b4befe"), ("pressed", COLOR_PRIMARY)], # Slightly lighter mauve on hover
        foreground=[("active", BG_MAIN)]
    )

    # Danger Button
    style.configure("Danger.TButton",
        background=COLOR_DANGER,
        foreground=BG_MAIN,
        bordercolor=COLOR_DANGER,
        padding=(PAD_MD, PAD_SM)
    )
    style.map("Danger.TButton",
        background=[("active", "#f5e0dc"), ("pressed", COLOR_DANGER)],
        foreground=[("active", BG_MAIN)]
    )

    # Entries (Inputs)
    style.configure("TEntry",
        fieldbackground=BG_INPUT,
        foreground=TXT_PRIMARY,
        bordercolor=BORDER_COLOR,
        lightcolor=BORDER_COLOR,
        darkcolor=BORDER_COLOR,
        padding=PAD_SM
    )
    style.map("TEntry",
        fieldbackground=[("focus", BG_INPUT_ACTIVE), ("!focus", BG_INPUT)],
        foreground=[("disabled", TXT_MUTED), ("!disabled", TXT_PRIMARY)],
        bordercolor=[("focus", COLOR_PRIMARY), ("!focus", BORDER_COLOR)],
        lightcolor=[("focus", COLOR_PRIMARY), ("!focus", BORDER_COLOR)],
        darkcolor=[("focus", COLOR_PRIMARY), ("!focus", BORDER_COLOR)]
    )
    
    # Checkbuttons
    style.configure("TCheckbutton",
        background=BG_MAIN,
        foreground=TXT_PRIMARY,
        focuscolor=COLOR_PRIMARY,
        indicatorbackground=BG_INPUT,
        indicatorcolor=BG_INPUT
    )
    style.map("TCheckbutton",
        background=[("active", BG_MAIN)],
        foreground=[("active", COLOR_PRIMARY)],
        indicatorbackground=[("selected", COLOR_PRIMARY), ("!selected", BG_INPUT)],
        indicatorcolor=[("selected", COLOR_PRIMARY), ("!selected", BG_INPUT)]
    )
    
    # Notebooks (Tabs)
    style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
    style.configure("TNotebook.Tab",
        background=BG_SIDEBAR,
        foreground=TXT_SECONDARY,
        padding=(PAD_MD, PAD_SM),
        borderwidth=0
    )
    style.map("TNotebook.Tab",
        background=[("selected", BG_MAIN), ("active", BG_INPUT)],
        foreground=[("selected", COLOR_PRIMARY), ("active", TXT_PRIMARY)]
    )
    
    # Comboboxes
    style.configure("TCombobox",
        fieldbackground=BG_INPUT,
        background=BG_INPUT,
        foreground=TXT_PRIMARY,
        bordercolor=BORDER_COLOR,
        arrowcolor=TXT_SECONDARY
    )
    style.map("TCombobox",
        fieldbackground=[("readonly", BG_INPUT), ("active", BG_INPUT_ACTIVE)],
        selectbackground=[("readonly", BG_INPUT)],
        foreground=[("readonly", TXT_PRIMARY), ("disabled", TXT_MUTED)],
        arrowcolor=[("active", COLOR_PRIMARY)],
        bordercolor=[("focus", COLOR_PRIMARY), ("!focus", BORDER_COLOR)],
        lightcolor=[("focus", COLOR_PRIMARY), ("!focus", BORDER_COLOR)],
        darkcolor=[("focus", COLOR_PRIMARY), ("!focus", BORDER_COLOR)]
    )

    # Scrollbars
    style.configure("Vertical.TScrollbar",
        background=BG_INPUT,
        bordercolor=BORDER_COLOR,
        troughcolor=BG_MAIN,
        arrowcolor=TXT_SECONDARY
    )
    style.map("Vertical.TScrollbar",
        background=[("active", BG_INPUT_ACTIVE)]
    )
