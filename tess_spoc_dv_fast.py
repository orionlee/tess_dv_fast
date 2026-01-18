"""
Fast Lookup of TESS-SPOC TCEs.
Unlike the SPOC TCEs, TESS-SPOC does not provide summary of TCE parameters, so
there is no metadata (e.g., period) available.

https://archive.stsci.edu/hlsp/tess-spoc
"""

# Volume note:
# for sectors 36-77, there is ~250K TCEs, the db is ~9Mb, while the csv is ~6Mb

import re
import sqlite3
from typing import Callable, Optional, Union

import numpy as np
import pandas as pd

from tess_dv_fast_common import ARRAY_LIKE_TYPES
from tess_spoc_dv_fast_spec import (
    DATA_BASE_DIR,
    TCESTATS_DBNAME,
)


def _query_tcestats_from_db(sql: str, **kwargs) -> pd.DataFrame:
    db_uri = f"file:{DATA_BASE_DIR}/{TCESTATS_DBNAME}?mode=ro"  # read-only
    with sqlite3.connect(db_uri, uri=True) as con:
        df = pd.read_sql(sql, con, **kwargs)
        # to avoid "PerformanceWarning: DataFrame is highly fragmented."
        # in subsequent codes such as _add_helpful_columns_to_tcestats()
        df = df.copy()
        return df


def _get_tcestats_of_tic_from_db(
    tic: Union[int, float, str, tuple, list],
) -> pd.DataFrame:
    if isinstance(tic, (int, float, str)) or np.isscalar(tic):
        return _query_tcestats_from_db(
            "select * from tess_spoc_tcestats where ticid = ?",
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
            f"select * from tess_spoc_tcestats where ticid in ({in_params_place_holder})",
            params=tic,
        )
    else:
        raise TypeError(
            f"tic must be a scalar or array-like. Actual type: {type(tic).__name__}"
        )


def _add_helpful_columns_to_tcestats(df: pd.DataFrame) -> None:
    def add_id(df):
        # add an ID column, analogous to exomast_id in SPOC TCEs
        # the format is exomast_id with a suffix (to signify it is from TESS-SPOC)
        df.insert(
            loc=0,
            column="id",
            value=(
                "TIC"
                + df["ticid"].astype(str)
                + df["sectors"].str.upper().str.replace("-", "")
                + "TCE"
                + df["tce_plnt_num"].astype(str)
                + "_F"  # mean FFI,  more succinct than a verbose _TESS-SPOC
            ),
        )

    def get_sectors_span(sectors_str):
        match = re.match(r"s(\d+)-s(\d+)", sectors_str)
        if match is None:
            return -1  # should not happen
        start, end = int(match[1]), int(match[2])

        return end - start + 1

    def dvs_fname(row):
        ticid, plnt_num, sectors = row.ticid, row.tce_plnt_num, row.sectors
        # zero-pad to the format needed
        ticid = str(ticid).zfill(16)
        plnt_num = str(plnt_num).zfill(2)
        return f"hlsp_tess-spoc_tess_phot_{ticid}-{sectors}_tess_v1_dvs-{plnt_num}.pdf"

    def dvm_fname(row):
        ticid, sectors = row.ticid, row.sectors
        # zero-pad to the format needed
        ticid = str(ticid).zfill(16)
        return f"hlsp_tess-spoc_tess_phot_{ticid}-{sectors}_tess_v1_dvm.pdf"

    def dvr_fname(row):
        ticid, sectors = row.ticid, row.sectors
        # zero-pad to the format needed
        ticid = str(ticid).zfill(16)
        return f"hlsp_tess-spoc_tess_phot_{ticid}-{sectors}_tess_v1_dvr.pdf"

    df["sectors_span"] = [get_sectors_span(s) for s in df["sectors"]]
    df["dvs"] = [dvs_fname(r) for _, r in df.iterrows()]
    df["dvm"] = [dvm_fname(r) for _, r in df.iterrows()]
    df["dvr"] = [dvr_fname(r) for _, r in df.iterrows()]
    add_id(df)

    return


def get_tce_infos_of_tic(
    tic: Union[int, float, str, tuple, list],
    tce_filter_func: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
) -> pd.DataFrame:
    # df = _read_tcestats_csv()  # for testing without db
    # df = df[df["ticid"] == tic]
    df = _get_tcestats_of_tic_from_db(tic)
    _add_helpful_columns_to_tcestats(df)
    # sort the result to the standard form
    # so that it is predictable for tce_filter_func
    df = df.sort_values(
        by=["ticid", "sectors_span", "id"], ascending=[True, False, True]
    )
    if tce_filter_func is not None and len(df) > 0:
        df = tce_filter_func(df)

    return df


def to_product_url(filename: str) -> str:
    """Convert the product filenames in columns such as dvs, dvr, etc., to URL to MAST server"""
    # e.g,  hlsp_tess-spoc_tess_phot_0000000033979459-s0056-s0069_tess_v1_dvs-01.pdf
    #       hlsp_tess-spoc_tess_phot_0000000033979459-s0056-s0069_tess_v1_dvm.pdf

    match = re.search(
        r"hlsp_tess-spoc_tess_phot_0+?(?P<ticid>[1-9]\d+)-(?P<sectors>s\d{4}-s\d{4})",
        filename,
    )

    sector_start, sector_end = match["sectors"].split("-")
    if sector_start == sector_end:
        # case single sector
        sectors = sector_start
    else:
        # case multi-sector
        sectors = match["sectors"]

    ticid = match["ticid"].zfill(16)
    # split the ticid into 4 parts for the sub directory pattern
    t1, t2, t3, t4 = ticid[0:4], ticid[4:8], ticid[8:12], ticid[12:16]

    return f"https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:HLSP/tess-spoc/{sectors}/target/{t1}/{t2}/{t3}/{t4}/{filename}"


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

    display_columns = [
        "id",
        # "ticid",
        # "tce_plnt_num",
        # "sectors",
        "dvs",
        "dvm",
        "dvr",
    ]

    if len(df["ticid"].unique()) > 1:
        # case multiple TICs in the result
        # prepend ticid to the columns to be displayed to differentiate between them
        display_columns = ["ticid"] + display_columns

    def format_id(id):
        # for TESS-SPOC, it is not available on ExoMAST, so we simply return a abbreviated ID
        short_name = re.sub(r"TIC\d+", "", id).lower()
        return short_name

    format_specs = {
        "id": format_id,
        "dvs": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvs</a>',
        "dvm": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvm</a>',
        "dvr": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvr</a>',
    }

    with pd.option_context(
        "display.max_colwidth", None, "display.max_rows", 999, "display.max_columns", 99
    ):
        styler = df[display_columns].style.format(format_specs).hide(axis="index")
        # hack to add units to the header
        html = styler.to_html()
        if return_as is None:
            from IPython.display import HTML, display

            return display(HTML(html))
        elif return_as == "html":
            return html
