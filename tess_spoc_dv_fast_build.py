"""Build and manage TESS-SPOC TCE master CSV and SQLite database."""

import os
from pathlib import Path
import re
import sqlite3
import shutil

import pandas as pd

from tess_spoc_dv_fast_spec import (
    DATA_BASE_DIR,
    TCESTATS_FILENAME,
    TCESTATS_DBNAME,
    sources_dv_sh_single_sector,
    sources_dv_sh_multi_sector,
)


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
        script_name = (
            f"{DATA_BASE_DIR}/hlsp_tess-spoc_tess_phot_{sector_start}_tess_v1_dl-dv.sh"
        )
    else:
        # case multi-sector
        script_name = (
            f"{DATA_BASE_DIR}/hlsp_tess-spoc_tess_phot_{sectors}_tess_v1_dl-dv.sh"
        )

    df = pd.read_csv(
        script_name,
        comment="#",
        sep=" ",
        names=["curl", "f", "create_dirs", "C", "output", "filename", "url"],
    )
    df = df[["filename"]]

    return df


def _get_tess_tcestats_csv(sectors_val):
    filename = _get_tess_dv_products_of_sectors(sectors_val)["filename"]
    # convert the list of filenames to a table that is subset of the SPOC csv,
    # - with columns ticid, tce_plnt_num, sectors,
    # - columns dvs, dvm, dvr skipped, as they can be dynamically created

    # we can get all the info needed from dvs pdf names
    dvs_filename = filename[filename.str.contains("_dvs")]
    dvs = dvs_filename.str.extract(
        rf"hlsp_tess-spoc_tess_phot_0+?(?P<ticid>[1-9]\d+)-s.+_tess_v1_dvs-0+?(?P<tce_plnt_num>[1-9]\d*).pdf"
    )
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


def download_all_data():
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
            url,
            filename=filename,
            download_dir=DATA_BASE_DIR,
            return_is_cache_used=True,
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


def _read_tcestats_csv():
    # the master csv is barebone, and meant to be used internally for converting to sqlite db
    csv_path = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}"
    return pd.read_csv(csv_path, comment="#")


def _export_tcestats_as_db():
    db_path_tmp = f"{DATA_BASE_DIR}/{TCESTATS_DBNAME}.tmp"
    db_path = f"{DATA_BASE_DIR}/{TCESTATS_DBNAME}"

    df = _read_tcestats_csv()

    Path(db_path_tmp).unlink(missing_ok=True)
    con = sqlite3.connect(db_path_tmp)
    try:  # use try / finally instead of with ... because sqlite3 context manager does not close the connection
        df.to_sql("tess_spoc_tcestats", con, if_exists="replace", index=False)

        sql_index = (
            "create index tess_spoc_tcestats_ticid on tess_spoc_tcestats(ticid);"
        )
        cursor = con.cursor()
        cursor.execute(sql_index)
        cursor.close()

        con.commit()
    finally:
        con.close()

    shutil.move(db_path_tmp, db_path)


# Build and update the DB / master csv from command line
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update master TESS-SPOC TCE data")
    parser.add_argument(
        "--update",
        dest="update",
        action="store_true",
        help="Update master csv and sqlite db.",
    )
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
