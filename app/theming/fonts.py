from __future__ import annotations

from PySide6.QtGui import QFontDatabase

DEFAULT_FONT_FAMILY = "Inter"

# Curated candidates, roughly best-looking first. Only ones actually installed on the
# user's machine are ever shown/used — we can't bundle font binaries here, so this list
# is filtered against QFontDatabase.families() at runtime by installed_fonts(). It's kept
# broad (popular Google Fonts + Windows/macOS/Linux system defaults) so most machines find
# a good handful of matches regardless of platform.
CANDIDATE_FONTS = [
    # Modern UI sans-serif (popular Google Fonts / app UI fonts)
    "Inter",
    "Roboto",
    "Open Sans",
    "Lato",
    "Montserrat",
    "Nunito",
    "Nunito Sans",
    "Poppins",
    "Work Sans",
    "Source Sans 3",
    "Source Sans Pro",
    "Rubik",
    "Karla",
    "Mulish",
    "DM Sans",
    "Manrope",
    "Raleway",
    "Barlow",
    "Quicksand",
    "PT Sans",
    "Noto Sans",
    "Fira Sans",
    "Ubuntu",
    "Cabin",
    "Heebo",
    "Hind",
    "Titillium Web",
    "Josefin Sans",
    # Windows system fonts
    "Segoe UI Variable",
    "Segoe UI",
    "Aptos",
    "Bahnschrift",
    "Calibri",
    "Cambria",
    "Candara",
    "Corbel",
    "Constantia",
    "Century Gothic",
    "Franklin Gothic Medium",
    "Gill Sans MT",
    # macOS system fonts
    "Helvetica Neue",
    "Helvetica",
    "Avenir",
    "Avenir Next",
    "Optima",
    "Gill Sans",
    # Cross-platform classics
    "Arial",
    "Verdana",
    "Tahoma",
    "Trebuchet MS",
    "Times New Roman",
    # Linux fallbacks
    "DejaVu Sans",
    "Liberation Sans",
    "Cantarell",
    # Serif options, for variety
    "Georgia",
    "Palatino Linotype",
    "Book Antiqua",
    "Garamond",
    "EB Garamond",
    "Playfair Display",
    "Merriweather",
    "Libre Baskerville",
    "Source Serif Pro",
    "PT Serif",
    "Noto Serif",
    "Lora",
    "Crimson Text",
    "Bitter",
    # Monospace, for variety
    "Consolas",
    "Cascadia Code",
    "Courier New",
]


def installed_fonts(candidates: list[str] = CANDIDATE_FONTS) -> list[str]:
    """The subset of `candidates` actually installed on this machine, in candidate order.
    Requires a QApplication/QGuiApplication to already exist."""
    available = set(QFontDatabase.families())
    found = [name for name in candidates if name in available]
    if not found:
        found = ["Segoe UI"] if "Segoe UI" in available else sorted(available)[:1]
    return found


def best_default_font(candidates: list[str] = CANDIDATE_FONTS) -> str:
    found = installed_fonts(candidates)
    return found[0] if found else DEFAULT_FONT_FAMILY
