"""Build and manage SPOC TCE master CSV and SQLite database."""

import os
import re
import shutil
import sqlite3
from pathlib import Path

import pandas as pd

from tess_dv_fast_spec import (
    DATA_BASE_DIR,
    TCESTATS_FILENAME,
    TCESTATS_DBNAME,
    sources_tcestats_single_sector,
    sources_tcestats_multi_sector,
    sources_dv_sh_single_sector,
    sources_dv_sh_multi_sector,
)


def _filename(url):
    match = re.search("[^/]+$", url)
    if match is not None:
        return match[0]
    else:
        raise ValueError(f"Failed to extract filename from url: {url}")


def _add_exomast_id(df):
    # id to construct exomast URL, e.g., TIC232646881S0073S0073TCE1
    # it can serves as a unique ID for the TCE across sectors too.
    df.insert(
        loc=0,
        column="exomast_id",
        value=(
            "TIC"
            + df["ticid"].astype(str)
            + df["sectors"].str.upper().str.replace("-", "")
            + "TCE"
            + df["tce_plnt_num"].astype(str)
        ),
    )


def _get_dv_products_of_sectors(sectors):
    # sectors: the value of sectors column in csv, e.g., s0002-s0072
    sector_start, sector_end = sectors.split("-")
    if sector_start == sector_end:
        # case single sector
        match = re.search(r"[1-9]\d+$", sectors)  # 2+ digits sector
        if match is not None:
            sector_str_in_filename = match[0]
        else:
            match = re.search("[1-9]$", sectors)  # single sector
            if match is not None:
                sector_str_in_filename = match[0]
            else:
                raise ValueError(f"Cannot prase sector from string {sectors}")
        script_name = f"{DATA_BASE_DIR}/tesscurl_sector_{sector_str_in_filename}_dv.sh"
    else:
        # case multi-sector
        script_name = f"{DATA_BASE_DIR}/tesscurl_multisector_{sectors}_dv.sh"

    filename = pd.read_csv(
        script_name,
        comment="#",
        sep=" ",
        names=["curl", "C", "-", "L", "o", "filename", "url"],
        usecols=["filename"],
    )["filename"]

    dvs_filename = filename[filename.str.contains("_dvs.pdf")]
    dvs = dvs_filename.str.extract(
        rf"tess\d+-{sectors}-0+?(?P<ticid>[1-9]\d+)-(?P<tce_plnt_num>\d\d)-"
    )
    dvs.ticid = dvs.ticid.astype("int64")
    dvs.tce_plnt_num = dvs.tce_plnt_num.astype(int)
    dvs["dvs"] = dvs_filename
    # in case multiple runs for the same TIC-sector, use the last one only
    dvs = dvs.groupby(by=["ticid", "tce_plnt_num"], as_index=False).last()

    def get_products_of_type(colname, filename_suffix):
        product_filename = filename[filename.str.contains(filename_suffix)]
        df = product_filename.str.extract(rf"tess\d+-{sectors}-0+?(?P<ticid>[1-9]\d+)-")
        df.ticid = df.ticid.astype("int64")
        df[colname] = product_filename
        # in case multiple runs for the same TIC-sector, use the last one only
        df = df.groupby(by="ticid", as_index=False).last()
        return df

    dvm = get_products_of_type("dvm", "_dvm.pdf")
    dvr = get_products_of_type("dvr", "_dvr.pdf")
    dvr_xml = get_products_of_type("dvr_xml", "_dvr.xml")
    dvt = get_products_of_type("dvt", "_dvt.fits")

    res = dvs
    for df in [dvm, dvr, dvr_xml, dvt]:
        res = pd.merge(res, df, on="ticid", how="left", validate="many_to_one")

    res["sectors"] = sectors
    _add_exomast_id(res)
    res.drop(["ticid", "tce_plnt_num", "sectors"], axis="columns", inplace=True)
    return res


RAW_CSV_COLS = "tceid,ticid,tce_plnt_num,sectors,lastUpdate,tce_period,tce_period_err,tce_time0bt,tce_time0bt_err,tce_time0,tce_time0_err,tce_ror,tce_ror_err,tce_dor,tce_dor_err,tce_incl,tce_incl_err,tce_impact,tce_impact_err,tce_duration,tce_duration_err,tce_ingress,tce_ingress_err,tce_depth,tce_depth_err,tce_eccen,tce_eccen_err,tce_longp,tce_longp_err,tce_limbdark_mod,tce_ldm_coeff1,tce_ldm_coeff2,tce_ldm_coeff3,tce_ldm_coeff4,tce_num_transits,tce_trans_mod,tce_full_conv,tce_model_snr,tce_model_chisq,tce_model_dof,tce_robstat,tce_dof2,tce_chisq2,tce_chisqgofdof,tce_chisqgof,tce_prad,tce_prad_err,tce_sma,tce_sma_err,tce_eqt,tce_eqt_err,tce_insol,tce_insol_err,tce_ntoi,tce_sectors,tce_steff,tce_steff_err,tce_slogg,tce_slogg_err,tce_smet,tce_smet_err,tce_sradius,tce_sradius_err,tce_sdensity,tce_sdensity_err,tce_steff_prov,tce_slogg_prov,tce_smet_prov,tce_sradius_prov,tce_sdensity_prov,tcet_period,tcet_period_err,tcet_time0bt,tcet_time0bt_err,tcet_time0,tcet_time0_err,tcet_duration,tcet_duration_err,tcet_ingress,tcet_ingress_err,tcet_depth,tcet_depth_err,tcet_full_conv,tcet_model_chisq,tcet_model_dof,wst_robstat,wst_depth,tce_ws_mesmedian,tce_ws_mesmad,tce_ws_maxmes,tce_ws_minmes,tce_ws_maxmesd,tce_ws_minmesd,tce_max_sngle_ev,tce_max_mult_ev,tce_bin_oedp_stat,tce_bin_spc_stat,tce_bin_lpc_stat,tce_albedo,tce_albedo_err,tce_ptemp,tce_ptemp_err,tce_albedo_stat,tce_ptemp_stat,boot_fap,boot_mesthresh,boot_mesmean,boot_messtd,bootstrap_transit_count,tce_cap_stat,tce_hap_stat,tce_dicco_mra,tce_dicco_mra_err,tce_dicco_mdec,tce_dicco_mdec_err,tce_dicco_msky,tce_dicco_msky_err,tce_ditco_mra,tce_ditco_mra_err,tce_ditco_mdec,tce_ditco_mdec_err,tce_ditco_msky,tce_ditco_msky_err"
RAW_CSV_COLS = RAW_CSV_COLS.split(",")


def _append_to_tcestats_csv(filepath, sectors_val, dest):
    print(f"DEBUG appending to master tcestats csv from: {filepath}")

    # base tcestats csv of a sector
    df = pd.read_csv(
        filepath,
        comment="#",
        # additional columns starting from s0095 / s0001-s0092
        # to get around the complication in the appended csv
        # use a fixed set of columns (from sector 1 csv)
        usecols=RAW_CSV_COLS,
    )

    if len(df.columns) != len(RAW_CSV_COLS):
        raise ValueError(
            (
                f"sector csv read is expected to have {len(RAW_CSV_COLS)} columns, actual={len(df.columns)}"
                f"\n{df.columns}"
            )
        )

    # replace sectors column with a uniform format, e.g., s0002-s0002
    # that describes the actual range for both single sector and multi sector csvs
    df["sectors"] = sectors_val

    # uniquely identify a TCE across all sectors
    _add_exomast_id(df)

    # include filenames of dvs, dvm, etc.
    df_filenames = _get_dv_products_of_sectors(sectors_val)
    df = pd.merge(df, df_filenames, on="exomast_id", validate="one_to_one")

    # only write header when the file is first created
    write_header = not os.path.isfile(dest)
    df.to_csv(dest, index=False, header=write_header, mode="a")


def download_all_data(minimal_db=False):
    """Download all relevant data locally."""
    import download_utils

    # TODO: scrape the listing pages to get the list of URLs, instead of hardcoded lists above

    # dv products download scripts (for urls to the products)
    # - they need to be first downloaded: as creating master csv below relies on the scripts
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

    # for tce stats csv files, download and merge them to a single csv
    # - first write to a temporary master csv. Once done, overwrite the existing master (if any)
    dest_csv_tmp = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}.tmp"
    dest_csv = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}"
    Path(dest_csv_tmp).unlink(missing_ok=True)
    for url in sources_tcestats_single_sector + sources_tcestats_multi_sector:
        filename = _filename(url)

        filepath, is_cache_used = download_utils.download_file(
            url,
            filename=filename,
            download_dir=DATA_BASE_DIR,
            return_is_cache_used=True,
        )
        if not is_cache_used:
            print(f"DEBUG Downloaded to {filepath} from: {url}")

        sectors_val = re.search(r"s\d{4}-s\d{4}", url)[0]  # e.g., s0002-s0002
        _append_to_tcestats_csv(filepath, sectors_val, dest_csv_tmp)
    shutil.move(dest_csv_tmp, dest_csv)

    # convert the master csv into a sqlite db for speedier query by ticid
    print(f"DEBUG Convert master tcestats csv to sqlite db, minimal_db={minimal_db}...")
    _export_tcestats_as_db(minimal_db)


# minimal list of columns in db in order to support display_tce_infos
# the resulting db is about 30% of the full db
_MIN_DB_COLS = [
    "exomast_id",
    "ticid",
    "tce_prad",  # for deriving: "Rp in Rj"
    "tce_time0bt",  #  "Epoch"
    "tce_period",  # "Period"
    "tce_duration",  # "Duration"
    "tce_impact",  # "Impact b"
    "tce_depth",  # for deriving "Depth"
    # for deriving "TicOffset"
    "tce_ditco_msky",
    "tce_ditco_msky_err",
    # for deriving "OotOffset",
    "tce_dicco_msky",
    "tce_dicco_msky_err",
    "dvs",  # will be replaced by generated version to save space
    # "dvm",  # will be generated
    # "dvr",  # will be generated
    "tce_sectors",  # for deriving "tce_num_sectors"
    # the following are components of a TCE's identifier, required
    # to generate dvs, dvm, dvr columns
    "tce_plnt_num",
    "sectors",
    # sellar radius provenance, used to determine if tce_depth is reliable,
    # by checking if the stellar radius is assumed to be solar or not
    "tce_sradius_prov",
]


def _read_tcestats_csv(**kwargs):
    # for ~230k rows of TCE stats data, it took 4-10secs, taking up 200+Mb memory.
    csv_path = f"{DATA_BASE_DIR}/{TCESTATS_FILENAME}"
    return pd.read_csv(csv_path, comment="#", dtype={"tce_sectors": str}, **kwargs)


def _export_tcestats_as_db(minimal_db=False):
    db_path_tmp = f"{DATA_BASE_DIR}/{TCESTATS_DBNAME}.tmp"
    db_path = f"{DATA_BASE_DIR}/{TCESTATS_DBNAME}"

    usecols = None if not minimal_db else _MIN_DB_COLS
    df = _read_tcestats_csv(
        usecols=usecols,
    )

    # create a column to flag if the stellar radius is assumed to be solar or not
    df["tce_sradius_prov_is_solar"] = df["tce_sradius_prov"] == "Solar"
    if minimal_db:
        df.drop(columns=["tce_sradius_prov"], inplace=True)

    if minimal_db:
        # replace dvs / dvm  / dvr columns with a much more compact representation
        match = df["dvs"].str.extract(r"tess(?P<date_time>\d+)-.+-(?P<pin>\d+)_dvs")
        # date_time: the associated timestamp
        # pin: the pipeline run
        # filename format reference: https://archive.stsci.edu/missions-and-data/tess/data-products
        df["_dv_date_time"] = match.date_time
        df["_dv_pin"] = match.pin.astype(int)
        # dvs, dvm, dvr can be dynamically derived from above columns and the existing TCE identifier columns
        df.drop(columns=["dvs"], inplace=True)

    Path(db_path_tmp).unlink(missing_ok=True)
    con = sqlite3.connect(db_path_tmp)
    try:  # use try / finally instead of with ... because sqlite3 context manager does not close the connection
        df.to_sql("tess_tcestats", con, if_exists="replace", index=False)

        # nice-to-have, but not critical
        sql_index = "create index tess_tcestats_ticid on tess_tcestats(ticid);"
        cursor = con.cursor()
        cursor.execute(sql_index)
        cursor.close()

        if minimal_db:  # create dvs, dvm, dvm as generated columns to save space
            # generated column is available from SQLite version 3.31.0 (2020-01-22).
            # So modern Python3 would all work.
            # https://www.sqlite.org/gencol.html
            # OPEN: Check sqlite version to guard against old version with `sqlite3.sqlite_version_info`
            cursor = con.cursor()
            cursor.executescript("""\
ALTER TABLE tess_tcestats
ADD COLUMN dvs GENERATED ALWAYS AS
('tess' || _dv_date_time || '-' || sectors || '-' || substr('0000000000000000'|| ticid, -16, 16)  || '-' ||  substr('00' || tce_plnt_num, -2, 2) || '-' ||  substr('00000' || _dv_pin, -5, 5) || '_dvs.pdf');

ALTER TABLE tess_tcestats
ADD COLUMN dvm GENERATED ALWAYS AS
('tess' || _dv_date_time || '-' || sectors || '-' || substr('0000000000000000'|| ticid, -16, 16)  || '-' ||  substr('00000' || _dv_pin, -5, 5) || '_dvm.pdf');

ALTER TABLE tess_tcestats
ADD COLUMN dvr GENERATED ALWAYS AS
('tess' || _dv_date_time || '-' || sectors || '-' || substr('0000000000000000'|| ticid, -16, 16)  || '-' ||  substr('00000' || _dv_pin, -5, 5) || '_dvr.pdf');
            """)
            cursor.close()

        con.commit()
    finally:
        con.close()

    shutil.move(db_path_tmp, db_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update master TESS TCE data")
    parser.add_argument(
        "--update",
        dest="update",
        action="store_true",
        help="Update master csv and sqlite db.",
    )
    parser.add_argument(
        "--minimal_db",
        dest="minimal_db",
        action="store_true",
        default=False,
        help="make the sqlite db minimal for typical use cases / webapp usage",
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
        print(f"Downloading data to create master csv, minimal_db={args.minimal_db}")
        download_all_data(minimal_db=args.minimal_db)
    else:
        print(f"Convert master csv to db, minimal_db={args.minimal_db}")
        _export_tcestats_as_db(args.minimal_db)
