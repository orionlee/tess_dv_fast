import os
from pathlib import Path
import re
import sqlite3
import shutil

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


"""
Fast Lookup of TESS-SPOC TCEs.
Unlike the SPOC TCEs, TESS-SPOC does not provide summary of TCE parameters, so
there is no metadata (e.g., period) available.

https://archive.stsci.edu/hlsp/tess-spoc
"""

DATA_BASE_DIR = f"{Path(__file__).parent}/data/tess_dv_fast"

TCESTATS_FILENAME = "tess_spoc_tcestats.csv"
TCESTATS_DBNAME = "tess_spoc_tcestats.db"


# Sources at: https://archive.stsci.edu/hlsp/tess-spoc

sources_dv_sh_single_sector = [
    ("https://archive.stsci.edu/hlsps/tess-spoc/download_scripts/"
     f"hlsp_tess-spoc_tess_phot_s{sec:04d}_tess_v1_dl-dv.sh") for sec in range(36, 77 + 1)
]


sources_dv_sh_multi_sector = [
    # the `s0056-s0069` appears to be mis-named. The content represents s0036-s0069
    "https://archive.stsci.edu/hlsps/tess-spoc/download_scripts/hlsp_tess-spoc_tess_phot_s0056-s0069_tess_v1_dl-dv.sh",

]


def _filename(url):
    match = re.search("[^/]+$", url)
    if match is not None:
        return match[0]
    else:
        raise ValueError(f"Failed to extract filename from url: {url}")


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


def _append_to_tcestats_csv(sectors_val, dest):
    print(f"DEBUG appending to master tess_spoc tcestats csv from: {sectors_val}")

    # the tcestats csv of a sector
    df = _get_tess_tcestats_csv(sectors_val)

    # only write header when the file is first created
    write_header = not os.path.isfile(dest)
    df.to_csv(dest, index=False, header=write_header, mode="a")


def download_all_data(minimal_db=False):
    """Download all relevant data locally."""
    import download_utils

    def get_sectors_val(filename):
        # eg, hlsp_tess-spoc_tess_phot_s0036_tess_v1_dl-dv.sh
        match = re.search(r"_(s\d{4})_tess", filename)
        if match is not None:
            return f"{match[1]}-{match[1]}"  # e.g., s0036-s0036

        # eg, hlsp_tess-spoc_tess_phot_s0056-s0069_tess_v1_dl-dv.sh
        match = re.search(r"_(s\d{4}-s\d{4})_tess", filename)
        if match is not None:
            return match[1]

    # dv products download scripts (for urls to the products)
    # - they need to be first downloaded: as creating master csv below relies on the scripts
    filename_list = []
    for url in sources_dv_sh_single_sector + sources_dv_sh_multi_sector:
        filename = _filename(url)
        filepath, is_cache_used = download_utils.download_file(
            url, filename=filename, download_dir=DATA_BASE_DIR, return_is_cache_used=True
        )
        if not is_cache_used:
            print(f"DEBUG Downloaded to {filepath} from: {url}")

        filename_list.append(filename)

    # for tce stats csv files, download and merge them to a single csv
    # - first write to a temporary master csv. Once done, overwrite the existing master (if any)
    dest_csv_tmp = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}.tmp"
    dest_csv = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}"
    Path(dest_csv_tmp).unlink(missing_ok=True)
    for filename in filename_list:
        sectors_val = get_sectors_val(filename)
        _append_to_tcestats_csv(sectors_val, dest_csv_tmp)
    shutil.move(dest_csv_tmp, dest_csv)

    # convert the master csv into a sqlite db for speedier query by ticid
    print(f"DEBUG Convert master tess-spoc tcestats csv to sqlite db...")
    _export_tcestats_as_db()


def _export_tcestats_as_db():
    db_path_tmp = f"{DATA_BASE_DIR}/{TCESTATS_DBNAME}.tmp"
    db_path = f"{DATA_BASE_DIR}/{TCESTATS_DBNAME}"

    df = _read_tcestats_csv()

    Path(db_path_tmp).unlink(missing_ok=True)
    con = sqlite3.connect(db_path_tmp)
    try:  # use try / finally instead of with ... because sqlite3 context manager does not close the connection
        df.to_sql("tess_spoc_tcestats", con, if_exists="replace", index=False)

        sql_index = "create index tess_spoc_tcestats_ticid on tess_spoc_tcestats(ticid);"
        cursor = con.cursor()
        cursor.execute(sql_index)
        cursor.close()

        con.commit()
    finally:
        con.close()

    shutil.move(db_path_tmp, db_path)


# Volume note:
# for sectors 36-77, there is ~250K TCEs, the db is ~9Mb, while the csv is ~6Mb
#
# Query Logic
#
def _read_tcestats_csv(**kwargs):
    # the master csv is barebone, and meant to be used internally for converting to sqlite db
    csv_path = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}"
    return pd.read_csv(csv_path, comment="#")


def _query_tcestats_from_db(sql, **kwargs):
    db_uri = f"file:{DATA_BASE_DIR}/{TCESTATS_DBNAME}?mode=ro"  # read-only
    with sqlite3.connect(db_uri, uri=True) as con:
        return pd.read_sql(sql, con, **kwargs)


def _get_tcestats_of_tic_from_db(tic):
    if isinstance(tic, (int, float, str)):
        return _query_tcestats_from_db(
            "select * from tess_spoc_tcestats where ticid = ?",
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
            f"select * from tess_spoc_tcestats where ticid in ({in_params_place_holder})",
            params=tic,
        )
    else:
        raise TypeError(f"tic must be a scalar or array-like. Actual type: {type(tic).__name__}")


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
    # df = _read_tcestats_csv()  # for testing without db
    # df = df[df["ticid"] == tic]
    df = _get_tcestats_of_tic_from_db(tic)
    _add_helpful_columns_to_tcestats(df)
    # sort the result to the standard form
    # so that it is predictable for tce_filter_func
    df = df.sort_values(by=["ticid", "sectors_span", "tce_plnt_num"], ascending=[True, False, True])
    if tce_filter_func is not None and len(df) > 0:
        df = tce_filter_func(df)

    return df


def to_product_url(filename):
    """Convert the product filenames in columns such as dvs, dvr, etc., to URL to MAST server"""
    # e.g,  hlsp_tess-spoc_tess_phot_0000000033979459-s0056-s0069_tess_v1_dvs-01.pdf
    #       hlsp_tess-spoc_tess_phot_0000000033979459-s0056-s0069_tess_v1_dvm.pdf

    match = re.search(r"hlsp_tess-spoc_tess_phot_0+?(?P<ticid>[1-9]\d+)-(?P<sectors>s\d{4}-s\d{4})", filename)

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


def display_tce_infos(df, return_as=None, no_tce_html=None):

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
        # for TESS-SPOC, it is not available on ExoMAST, so we simply return a abbrevated ID
        short_name = re.sub(r"TIC\d+", "", id).lower()
        return short_name

    format_specs = {
        "id": format_id,
        "dvs": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvs</a>',
        "dvm": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvm</a>',
        "dvr": lambda f: f'<a target="_blank" href="{to_product_url(f)}">dvr</a>',
    }

    with pd.option_context("display.max_colwidth", None, "display.max_rows", 999, "display.max_columns", 99):
        styler = df[display_columns].style.format(format_specs).hide(axis="index")
        # hack to add units to the header
        html = styler.to_html()
        if len(df) < 1 and no_tce_html is not None:
            html = no_tce_html
        if return_as is None:
            from IPython.display import display, HTML

            return display(HTML(html))
        elif return_as == "html":
            return html


# update the DB / master csv from command line
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update master TESS-SPOC TCE data")
    parser.add_argument("--update", dest="update", action="store_true", help="Update master csv and sqlite db.")
    parser.add_argument(
        "--db_only",
        dest="db_only",
        action="store_true",
        default=False,
        help="only convert the local master csv to sqlite db, without rebuilding the csv from sources",
    )

    args = parser.parse_args()
    if not args.update:
        print("--update must be specified")
        parser.print_help()
        parser.exit()

    if not args.db_only:
        print(f"Downloading data to create master csv and sqlite db")
        download_all_data()
    else:
        # primarily for debugging
        print(f"Convert master tess-spoc csv to db")
        _export_tcestats_as_db()

