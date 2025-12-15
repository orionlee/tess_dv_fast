"""
Fast Lookup of SPOC TCEs from TESS mission.

https://archive.stsci.edu/missions-and-data/tess
"""

import re
import sqlite3

import numpy as np
import pandas as pd

try:
    from astropy.table import Column

    _HAS_ASTROPY = False
except Exception:
    _HAS_ASTROPY = False

# for tic parameter in get_tce_infos_of_tic(), case a list of TICs
#
# Note: use list, tuple explicitly, instead of collection.abc.Sequence,
# because types such as str also implements Sequence
if _HAS_ASTROPY:
    _ARRAY_LIKE_TYPES = (list, tuple, set, np.ndarray, pd.Series, Column)
else:
    _ARRAY_LIKE_TYPES = (list, tuple, set, np.ndarray, pd.Series)


from tess_dv_fast_spec import (
    DATA_BASE_DIR,
    TCESTATS_FILENAME,
    TCESTATS_DBNAME,
    sources_tcestats_single_sector,
    sources_tcestats_multi_sector,
)


def get_high_watermarks():
    latest_single_sector_url = sources_tcestats_single_sector[-1]
    latest_single_sector_match = re.search(r"(s\d+)_dvr-tcestats", latest_single_sector_url)
    if latest_single_sector_match is not None:
        latest_single_sector = latest_single_sector_match[1]

    latest_multi_sector_url = sources_tcestats_multi_sector[-1]
    latest_multi_sector_match = re.search(r"(s\d+-s\d+)_dvr-tcestats", latest_multi_sector_url)
    if latest_multi_sector_match is not None:
        latest_multi_sector = latest_multi_sector_match[1]

    return dict(single_sector=latest_single_sector, multi_sector=latest_multi_sector)


def read_tcestats_csv(**kwargs):
    # for ~230k rows of TCE stats data, it took 4-10secs, taking up 200+Mb memory.
    csv_path = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}"
    return pd.read_csv(csv_path, comment="#", dtype={"tce_sectors": str}, **kwargs)


def _query_tcestats_from_db(sql, **kwargs):
    db_uri = f"file:{DATA_BASE_DIR}/{TCESTATS_DBNAME}?mode=ro"  # read-only
    with sqlite3.connect(db_uri, uri=True) as con:
        return pd.read_sql(sql, con, **kwargs)


def _get_tcestats_of_tic_from_db(tic):
    # OPEN: support optional columns parameter?
    # - double quote the column names in the constructed SQL
    #   would be sufficient wo avoid SQL injection
    # - need to make _add_helpful_columns_to_tcestats()
    #   handle missing columns though
    if isinstance(tic, (int, float, str)):
        return _query_tcestats_from_db(
            "select * from tess_tcestats where ticid = ?",
            params=[tic],
        )
    elif isinstance(tic, _ARRAY_LIKE_TYPES):
        #
        # convert to sqlite driver acceptable type
        # 1. list, and
        # 2. of type `int`, e.g., using `np.int32` would result in no match
        #    (probably requires registering some conversion in the driver)
        tic = [int(v) for v in tic]
        in_params_place_holder = ",".join(["?" for i in range(len(tic))])
        return _query_tcestats_from_db(
            f"select * from tess_tcestats where ticid in ({in_params_place_holder})",
            params=tic,
        )
    else:
        raise TypeError(f"tic must be a scalar or array-like. Actual type: {type(tic).__name__}")


def get_tce_infos_of_tic(tic, tce_filter_func=None):
    df = _get_tcestats_of_tic_from_db(tic)
    _add_helpful_columns_to_tcestats(df)
    # sort the result to the standard form
    # so that it is predictable for tce_filter_func
    df = df.sort_values(by=["ticid", "sectors_span", "exomast_id"], ascending=[True, False, True])
    if tce_filter_func is not None and len(df) > 0:
        df = tce_filter_func(df)

    return df


R_EARTH_TO_R_JUPITER = 6378.1 / 71492


def _add_helpful_columns_to_tcestats(df):
    def get_sectors_span(sectors_str):
        match = re.match(r"s(\d+)-s(\d+)", sectors_str)
        if match is None:
            return -1  # should not happen
        start, end = int(match[1]), int(match[2])

        return end - start + 1

    # convert the bit pattern in tce_sectors column to number of sectors a TCE covers
    df["tce_num_sectors"] = df["tce_sectors"].str.count("1")
    # OPEN: column "sectors_span" is added as a workaround to
    # ensure the default sort (TCEs with most sectors come first) work properly
    #
    # Root cause: it appears that in MAST-supplied csv,
    # the value of the column "tce_sectors" is inaccurate for long multi-sector ones
    # such that the values beyond sector 79 is missing.
    # Example: TIC 336824844, for s0014-s0086 shows up after s0014-s0078 using tce_num_sectors
    # as the "tce_sectors" value for s0014-s0086 is inaccurate.
    # As a result,the value derived column "tce_num_sectors" for the
    # recent long multi-sector TCEs (starting from s0014-s0086).
    #
    # Workaround solution:
    # add a new column "sectors_span" that count the span of a (multi-sector) TCE,
    # e.g., for s0014-0086, it is 86 - 14 + 1 = 73
    #
    df["sectors_span"] = [get_sectors_span(s) for s in df["sectors"]]
    df["tce_prad_jup"] = df["tce_prad"] * R_EARTH_TO_R_JUPITER
    df["tce_depth_pct"] = df["tce_depth"] / 10000
    df["tce_ditco_msky_sig"] = df["tce_ditco_msky"] / df["tce_ditco_msky_err"]  # TicOffset sig
    df["tce_dicco_msky_sig"] = df["tce_dicco_msky"] / df["tce_dicco_msky_err"]  # OotOffset sig
    # Note: model's stellar density, `starDensitySolarDensity` in dvr xml, is not available in csv


def to_product_url(filename):
    """Convert the product filenames in columns such as dvs, dvr, etc., to URL to MAST server"""
    return f"https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:TESS/product/{filename}"


def display_tce_infos(df, return_as=None, no_tce_html=None):
    df["Codes"] = (
        "epoch=" + df["tce_time0bt"].astype(str) + ", "
        "duration_hr=" + df["tce_duration"].astype(str) + ", "
        "period=" + df["tce_period"].astype(str) + ", "
        "label=" + '"' + df["exomast_id"].str.replace(r"TIC\d+", "", regex=True).str.lower() + '", '
        "transit_depth_percent=" + df["tce_depth_pct"].map("{:.4f}".format) + ","
    )

    df = df.rename(
        columns={
            "tce_prad_jup": "Rp",
            "tce_time0bt": "Epoch",
            "tce_period": "Period",
            "tce_duration": "Duration",
            "tce_impact": "Impact b",
            "tce_depth_pct": "Depth",
        }
    )

    df["TicOffset"] = df["tce_ditco_msky"].astype(str) + "|" + df["tce_ditco_msky_sig"].astype(str)
    df["OotOffset"] = df["tce_dicco_msky"].astype(str) + "|" + df["tce_dicco_msky_sig"].astype(str)

    display_columns = [
        "exomast_id",
        # "ticid",
        # "tce_plnt_num",
        # "sectors",
        # "tce_num_sectors",
        "dvs",
        "dvm",
        "dvr",
        "Rp",
        "Epoch",
        "Duration",
        "Period",
        "Depth",
        "Impact b",
        "TicOffset",
        "OotOffset",
        "Codes",
    ]

    if len(df["ticid"].unique()) > 1:
        # case multiple TICs in the result
        # prepend ticid to the columns to be displayed to differentiate between them
        display_columns = ["ticid"] + display_columns

    def format_exomast_id(id):
        short_name = re.sub(r"TIC\d+", "", id).lower()
        return f'<a target="_exomast" href="https://exo.mast.stsci.edu/exomast_planet.html?planet={id}">{short_name}</a>'

    def format_offset_n_sigma(val_sigma_str):
        # format TicOffset / OotOffset, to value (sigma)
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
        return f"""\
<input type="text" style="margin-left: 3ch; font-size: 90%; color: #666; width: 10ch;"
    onclick="this.select();" readonly value='{codes}'>"""

    format_specs = {
        "exomast_id": format_exomast_id,
        "dvs": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvs</a>',
        "dvm": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvm</a>',
        "dvr": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvr</a>',
        "Rp": "{:.3f}",
        "Epoch": "{:.2f}",  # the csv has 2 digits precision
        "Duration": "{:.4f}",
        "Period": "{:.6f}",
        "Depth": "{:.4f}",
        "Impact b": "{:.2f}",
        "TicOffset": format_offset_n_sigma,
        "OotOffset": format_offset_n_sigma,
        "Codes": format_codes,
    }

    with pd.option_context("display.max_colwidth", None, "display.max_rows", 999, "display.max_columns", 99):
        styler = df[display_columns].style.format(format_specs).hide(axis="index")
        # hack to add units to the header
        html = styler.to_html()
        html = html.replace(">Rp</th>", ">R<sub>p</sub><br>R<sub>j</sub></th>", 1)
        html = html.replace(">Epoch</th>", ">Epoch<br>BTJD</th>", 1)
        html = html.replace(">Duration</th>", ">Duration<br>hr</th>", 1)
        html = html.replace(">Period</th>", ">Period<br>day</th>", 1)
        html = html.replace(">Depth</th>", ">Depth<br>%</th>", 1)
        html = html.replace(">TicOffset</th>", '>TicOffset<br>" (σ)</th>', 1)
        html = html.replace(">OotOffset</th>", '>OotOffset<br>" (σ)</th>', 1)
        if len(df) < 1 and no_tce_html is not None:
            html = no_tce_html
        if return_as is None:
            from IPython.display import display, HTML

            return display(HTML(html))
        elif return_as == "html":
            return html
