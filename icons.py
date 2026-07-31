"""Small inline-SVG icon set for the studio UI. All icons share a 24x24
viewBox, stroke-based line style (stroke="currentColor", fill="none"),
so they inherit whatever color the caller sets via CSS `color`. Keeping
these as plain strings (rendered with |safe in templates) avoids pulling
in an icon font or external icon library just for ~20 glyphs.
"""

_STROKE = 'stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"'


def _svg(inner: str) -> str:
    return f'<svg viewBox="0 0 24 24" {_STROKE}>{inner}</svg>'


# --- Sidebar / chrome icons -------------------------------------------------

NAV_ICONS = {
    "create": _svg(
        '<circle cx="12" cy="12" r="9.5"/><line x1="12" y1="7.5" x2="12" y2="16.5"/><line x1="7.5" y1="12" x2="16.5" y2="12"/>'
    ),
    "library": _svg(
        '<rect x="3" y="3" width="7.5" height="7.5" rx="1.5"/>'
        '<rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5"/>'
        '<rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5"/>'
        '<rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5"/>'
    ),
    "presets": _svg(
        '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>'
    ),
    "exports": _svg(
        '<path d="M12 3v12"/><polyline points="7 10 12 15 17 10"/><path d="M5 19h14"/>'
    ),
    "settings": _svg(
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.7 1.7 0 00.3 1.9l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.9-.3 1.7 1.7 0 00-1 1.6V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.9.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.9 1.7 1.7 0 00-1.6-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.9.3H9a1.7 1.7 0 001-1.6V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.6 1.7 1.7 0 001.9-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.9V9a1.7 1.7 0 001.6 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.6 1z"/>'
    ),
    "mic": _svg(
        '<rect x="9" y="2" width="6" height="12" rx="3"/>'
        '<path d="M5 11a7 7 0 0014 0"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/>'
    ),
    "search": _svg('<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'),
    "chevron-right": _svg('<polyline points="9 18 15 12 9 6"/>'),
    "chevron-down": _svg('<polyline points="6 9 12 15 18 9"/>'),
    "arrow-right": _svg('<line x1="4" y1="12" x2="20" y2="12"/><polyline points="14 6 20 12 14 18"/>'),
}


# --- Category icons ----------------------------------------------------------

_LOTUS = (
    '<g>'
    + ''.join(
        f'<path d="M12 12 C10.2 8.4 10.2 4.6 12 2 C13.8 4.6 13.8 8.4 12 12 Z" transform="rotate({a} 12 12)"/>'
        for a in (0, 60, 120, 180, 240, 300)
    )
    + '<circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none"/></g>'
)

CATEGORY_ICONS = {
    "Chakras": _svg(_LOTUS),
    "Emotional & Spiritual (Solfeggio)": _svg(
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
    ),
    "Mental & Emotional": _svg(
        '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/>'
        '<line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>'
    ),
    "Brainwave States": _svg('<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'),
    "Cardiovascular & Circulation": _svg(
        '<path d="M20.8 4.6a5.5 5.5 0 00-7.8 0L12 5.6l-1-1a5.5 5.5 0 00-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 000-7.8z"/>'
    ),
    "Detox & Vitality": _svg(
        '<path d="M20.24 12.24a6 6 0 00-8.49-8.49L5 10.5V19h8.5z"/>'
        '<line x1="16" y1="8" x2="2" y2="22"/><line x1="17.5" y1="15" x2="9" y2="15"/>'
    ),
    "Digestive & Gut": _svg('<circle cx="12" cy="12" r="9.5"/><circle cx="12" cy="12" r="3.2"/>'),
    "Ears, Eyes, Mouth & Throat": _svg(
        '<path d="M1.5 12S5.5 4 12 4s10.5 8 10.5 8-4 8-10.5 8-10.5-8-10.5-8z"/><circle cx="12" cy="12" r="3"/>'
    ),
    "Hormonal & Metabolic": _svg('<path d="M12 2.5s7 8.7 7 13.2a7 7 0 01-14 0c0-4.5 7-13.2 7-13.2z"/>'),
    "Immune & Infection": _svg('<path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z"/>'),
    "Musculoskeletal": _svg(
        '<circle cx="12" cy="5" r="2.3"/><line x1="12" y1="7.3" x2="12" y2="21"/>'
        '<path d="M5 13a7 7 0 0014 0"/><line x1="5" y1="13" x2="8" y2="13"/><line x1="16" y1="13" x2="19" y2="13"/>'
    ),
    "Nervous System & Brain": _svg('<polygon points="13 2 3 14 11 14 9 22 21 10 13 10 13 2"/>'),
    "Pain & Inflammation": _svg(
        '<path d="M14 4v10.6a4 4 0 11-4 0V4a2 2 0 014 0z"/><line x1="12" y1="9" x2="12" y2="16"/>'
    ),
    "Parasites & Fungal": _svg(
        '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/>'
    ),
    "Reproductive & Urinary": _svg('<path d="M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z"/>'),
    "Respiratory": _svg(
        '<path d="M3 8h11a3 3 0 100-3"/><path d="M3 12h15a3 3 0 110 3"/><path d="M3 16h9a2 2 0 110 2"/>'
    ),
    "Skin & Hair": _svg(
        '<circle cx="12" cy="12" r="4.3"/>'
        '<g stroke-width="1.6">'
        '<line x1="12" y1="1.5" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22.5"/>'
        '<line x1="4.2" y1="4.2" x2="6" y2="6"/><line x1="18" y1="18" x2="19.8" y2="19.8"/>'
        '<line x1="1.5" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22.5" y2="12"/>'
        '<line x1="4.2" y1="19.8" x2="6" y2="18"/><line x1="18" y1="6" x2="19.8" y2="4.2"/>'
        '</g>'
    ),
}

_DEFAULT_ICON = _svg('<circle cx="12" cy="12" r="9"/>')

# Muted, dark-mode-friendly accent per category so browse cards feel
# hand-curated rather than monochrome. Cycled by category order.
_PALETTE = ["#8fd6b4", "#e2a0b8", "#9db8e0", "#e0c07e", "#c3a6e0", "#7fd0c9", "#e0a37f"]


def category_icon(name: str) -> str:
    return CATEGORY_ICONS.get(name, _DEFAULT_ICON)


def category_color(index: int) -> str:
    return _PALETTE[index % len(_PALETTE)]
