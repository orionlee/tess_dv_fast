import os
from pathlib import Path
import re
import sqlite3
import shutil

import numpy as np
import pandas as pd

"""
Fast Lookup of TESS-SPOC TCEs.
Unlike the SPOC TCEs, TESS-SPOC does not provide summary of TCE parameters, so
there is no metadata (e.g., period) available.

https://archive.stsci.edu/hlsp/tess-spoc
"""

DATA_BASE_DIR = f"{Path(__file__).parent}/data/tess_dv_fast"

TCESTATS_FILENAME = "tess_spoc_tcestats.csv"
TCESTATS_DBNAME = "tess_spoc_tcestats.db"


def _get_tess_dv_products_of_sectors(sectors):
    # sectors: the value of sectors column in csv, e.g., s0001-s0001, s0002-s0072
    sector_start, sector_end = sectors.split("-")
    if sector_start == sector_end:
        # case single sector
        script_name = f"{DATA_BASE_DIR}/hlsp_tess-spoc_tess_phot_{sector_start}_tess_v1_dl-dv.sh"
    else:
        # case multi-sector
        script_name = f"{DATA_BASE_DIR}/hlsp_tess-spoc_tess_phot_{sectors}_tess_v1_dl-dv.sh"

    df = pd.read_csv(
        script_name,
        comment="#",
        sep=" ",
        names=["curl", "f", "create_dirs", "C", "output", "filename", "url"],
        # usecols=["filename"],
    )
    # somehow `usecols=["filename"]` failed with
    # ValueError: Number of passed names did not match number of header fields in the file
    df = df[["filename"]]

    return df


def _get_tess_tcestats_csv(sectors_val):
    filename = _get_tess_dv_products_of_sectors(sectors_val)["filename"]
    # convert the list of filenames to a table that is subset of the SPOC csv,
    # - with columns ticid, tce_plnt_num, sectors,
    # - columns dvs, dvm, dvr skipped, as they can be dynamically created

    # we can get all the info needed from dvs pdf names
    dvs_filename = filename[filename.str.contains("_dvs")]
    dvs = dvs_filename.str.extract(rf"hlsp_tess-spoc_tess_phot_0+?(?P<ticid>[1-9]\d+)-s.+_tess_v1_dvs-0+?(?P<tce_plnt_num>[1-9]\d*).pdf")
    dvs.ticid = dvs.ticid.astype("int64")
    dvs.tce_plnt_num = dvs.tce_plnt_num.astype(int)

    # in case multiple runs for the same TIC-sector, use the last one only
    dvs = dvs.groupby(by=["ticid", "tce_plnt_num"], as_index=False).last()
    dvs["sectors"] = sectors_val

    return dvs


def _add_helpful_columns_to_tcestats(df):
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


def get_tce_infos_of_tic(tic, tce_filter_func=None):
    # df = _get_tcestats_of_tic_from_db(tic)  # TODO:
    df = _get_tess_tcestats_csv("s0056-s0069")  # "s0036-s0036"  # temporary for testing
    df = df[df["ticid"] == tic]
    _add_helpful_columns_to_tcestats(df)
    # sort the result to the standard form
    # so that it is predictable for tce_filter_func
    df = df.sort_values(by=["ticid", "sectors_span", "tce_plnt_num"], ascending=[True, False, True])
    if tce_filter_func is not None and len(df) > 0:
        df = tce_filter_func(df)

    return df

