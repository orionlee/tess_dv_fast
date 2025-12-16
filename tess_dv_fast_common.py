"""
Common constants, utilities, and display functions shared across TESS DV Fast modules.
"""

import re

import numpy as np
import pandas as pd

try:
    from astropy.table import Column

    _HAS_ASTROPY = True
except Exception:
    _HAS_ASTROPY = False

# for tic parameter in get_tce_infos_of_tic(), case a list of TICs
#
# Note: use list, tuple explicitly, instead of collection.abc.Sequence,
# because types such as str also implements Sequence
if _HAS_ASTROPY:
    ARRAY_LIKE_TYPES = (list, tuple, set, np.ndarray, pd.Series, Column)
else:
    ARRAY_LIKE_TYPES = (list, tuple, set, np.ndarray, pd.Series)

# Physical constants
R_EARTH_TO_R_JUPITER = 6378.1 / 71492


# Common Pandas Display formatters
def format_exomast_id(id_str):
    """Format exomast_id as a clickable link."""
    short_name = re.sub(r"TIC\d+", "", id_str).lower()
    return f'<a target="_exomast" href="https://exo.mast.stsci.edu/exomast_planet.html?planet={id_str}">{short_name}</a>'


def format_offset_n_sigma(val_sigma_str):
    """Format TicOffset / OotOffset as value (sigma) with color coding."""
    try:
        if val_sigma_str == "0.0|-0.0":
            # special case TCE has no offset, indicated by offset == 0 and error == -1 in the source csv
            return "N/A"
        val, sigma = val_sigma_str.split("|")
        val = float(val)
        sigma = float(sigma)
        if sigma >= 3:
            sigma_style = ' style="color: red; font-weight: bold;"'
        else:
            sigma_style = ""
        return f"{val:.0f} <span{sigma_style}>({sigma:.1f})</span>"
    except Exception:
        # in case something unexpected, fallback to raw str to avoid exception in display
        return val_sigma_str


def format_codes(codes):
    """Format codes as a clickable text input field."""
    return f"""\
<input type="text" style="margin-left: 3ch; font-size: 90%; color: #666; width: 10ch;"
    onclick="this.select();" readonly value='{codes}'>"""


def format_product_url(to_product_url_func):
    """Return a formatter function for product links (dvs, dvm, dvr)."""
    def _format(filename):
        return f'<a target="_blank" href="{to_product_url_func(filename)}">{filename[-10:]}</a>'
    return _format


def add_html_column_units(html):
    """Add HTML units to column headers in a styled dataframe table."""
    html = html.replace(">Rp</th>", ">R<sub>p</sub><br>R<sub>j</sub></th>", 1)
    html = html.replace(">Epoch</th>", ">Epoch<br>BTJD</th>", 1)
    html = html.replace(">Duration</th>", ">Duration<br>hr</th>", 1)
    html = html.replace(">Period</th>", ">Period<br>day</th>", 1)
    html = html.replace(">Depth</th>", ">Depth<br>%</th>", 1)
    html = html.replace(">TicOffset</th>", '>TicOffset<br>" (σ)</th>', 1)
    html = html.replace(">OotOffset</th>", '>OotOffset<br>" (σ)</th>', 1)
    return html
