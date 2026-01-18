"""
Fast Lookup of SPOC TCEs from TESS mission.

https://archive.stsci.edu/missions-and-data/tess
"""

import re
import sqlite3
from typing import Callable, Optional, Union

import numpy as np
import pandas as pd

from tess_dv_fast_common import (
    ARRAY_LIKE_TYPES,
    R_EARTH_TO_R_JUPITER,
    add_html_column_units,
    format_codes,
    format_exomast_id,
    format_offset_n_sigma,
)
from tess_dv_fast_spec import (
    DATA_BASE_DIR,
    TCESTATS_DBNAME,
    TCESTATS_FILENAME,
)


def read_tcestats_csv(**kwargs) -> pd.DataFrame:
    # for ~230k rows of TCE stats data, it took 4-10secs, taking up 200+Mb memory.
    csv_path = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}"
    return pd.read_csv(csv_path, comment="#", dtype={"tce_sectors": str}, **kwargs)


def _query_tcestats_from_db(sql: str, **kwargs) -> pd.DataFrame:
    db_uri = f"file:{DATA_BASE_DIR}/{TCESTATS_DBNAME}?mode=ro"  # read-only
    with sqlite3.connect(db_uri, uri=True) as con:
        # convert the 0/1 value in column `tce_sradius_prov_is_solar` to bool
        df = pd.read_sql(sql, con, dtype={"tce_sradius_prov_is_solar": bool}, **kwargs)
        # to avoid "PerformanceWarning: DataFrame is highly fragmented."
        # in subsequent codes such as _add_helpful_columns_to_tcestats()
        df = df.copy()
        return df


def _get_tcestats_of_tic_from_db(
    tic: Union[int, float, str, tuple, list],
) -> pd.DataFrame:
    # OPEN: support optional columns parameter?
    # - double quote the column names in the constructed SQL
    #   would be sufficient wo avoid SQL injection
    # - need to make _add_helpful_columns_to_tcestats()
    #   handle missing columns though
    if isinstance(tic, (int, float, str)) or np.isscalar(tic):
        return _query_tcestats_from_db(
            "select * from tess_tcestats where ticid = ?",
            params=[int(tic)],
        )
    elif isinstance(tic, ARRAY_LIKE_TYPES):
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
        raise TypeError(
            f"tic must be a scalar or array-like. Actual type: {type(tic).__name__}"
        )


def get_tce_infos_of_tic(
    tic: Union[int, float, str, tuple, list],
    tce_filter_func: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
) -> pd.DataFrame:
    df = _get_tcestats_of_tic_from_db(tic)
    _add_helpful_columns_to_tcestats(df)
    # sort the result to the standard form
    # so that it is predictable for tce_filter_func
    df = df.sort_values(
        by=["ticid", "sectors_span", "exomast_id"], ascending=[True, False, True]
    )
    if tce_filter_func is not None and len(df) > 0:
        df = tce_filter_func(df)

    return df


def _add_helpful_columns_to_tcestats(df: pd.DataFrame) -> None:
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
    df["tce_ditco_msky_sig"] = (
        df["tce_ditco_msky"] / df["tce_ditco_msky_err"]
    )  # TicOffset sig
    df["tce_dicco_msky_sig"] = (
        df["tce_dicco_msky"] / df["tce_dicco_msky_err"]
    )  # OotOffset sig
    # Note: model's stellar density, `starDensitySolarDensity` in dvr xml, is not available in csv


def to_product_url(filename: str) -> str:
    """Convert the product filenames in columns such as dvs, dvr, etc., to URL to MAST server"""
    return f"https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:TESS/product/{filename}"


def _format_Rp(val_str):
    # val_str is concatenated in the form of <Rp>|<sradius_is_solar>
    pradius, sradius_is_solar = val_str.split("|")
    pradius = f"{float(pradius):.4f}"
    if sradius_is_solar == "True":
        return f'<span style="color: red; font-weight: bold;">{pradius}<span>'
    else:
        return pradius


def display_tce_infos(
    df: pd.DataFrame,
    return_as: Optional[str] = None,
    no_tce_html: Optional[str] = "",
) -> Optional[Union[str, None]]:
    if df is None or len(df) < 1:
        if return_as is None:
            from IPython.display import HTML, display

            return display(HTML(no_tce_html))
        elif return_as == "html":
            return no_tce_html

    df = (
        df.copy()
    )  # avoid pandas warning for cases the df is a slice of an underlying df
    df["Codes"] = (
        "epoch=" + df["tce_time0bt"].astype(str) + ", "
        "duration_hr=" + df["tce_duration"].astype(str) + ", "
        "period=" + df["tce_period"].astype(str) + ", "
        "label="
        + '"'
        + df["exomast_id"].str.replace(r"TIC\d+", "", regex=True).str.lower()
        + '", '
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

    df["TicOffset"] = (
        df["tce_ditco_msky"].astype(str) + "|" + df["tce_ditco_msky_sig"].astype(str)
    )
    df["OotOffset"] = (
        df["tce_dicco_msky"].astype(str) + "|" + df["tce_dicco_msky_sig"].astype(str)
    )

    df["Rp"] = df["Rp"].astype(str) + "|" + df["tce_sradius_prov_is_solar"].astype(str)

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

    format_specs = {
        "exomast_id": format_exomast_id,
        "dvs": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvs</a>',
        "dvm": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvm</a>',
        "dvr": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvr</a>',
        "Rp": _format_Rp,
        "Epoch": "{:.2f}",  # the csv has 2 digits precision
        "Duration": "{:.4f}",
        "Period": "{:.6f}",
        "Depth": "{:.4f}",
        "Impact b": "{:.2f}",
        "TicOffset": format_offset_n_sigma,
        "OotOffset": format_offset_n_sigma,
        "Codes": format_codes,
    }

    with pd.option_context(
        "display.max_colwidth", None, "display.max_rows", 999, "display.max_columns", 99
    ):
        styler = df[display_columns].style.format(format_specs).hide(axis="index")
        html = add_html_column_units(styler.to_html())
        if return_as is None:
            from IPython.display import HTML, display

            return display(HTML(html))
        elif return_as == "html":
            return html
