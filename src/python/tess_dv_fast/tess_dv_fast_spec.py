"""TESS TCE (SPOC) data specifications and source URLs."""

import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_BASE_PATH = os.environ.get("TESS_DB_BASE_PATH", "./")
DATA_BASE_DIR = str((Path(_BASE_PATH) / "data" / "tess_dv_fast").resolve())

TCESTATS_FILENAME = "tess_tcestats.csv"
TCESTATS_DBNAME = "tess_tcestats.db"
SOURCE_URLS_FILENAME = "tess_dv_fast_spec.json"

# csv source: https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_tce.html
# sh source: https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_ffi-tp-lc-dv.html
def __getattr__(name: str):
    """Provide attributes `sources_tcestats_single_sector` , `sources_tcestats_multi_sector`,
    `sources_dv_sh_single_sector`, `sources_dv_sh_multi_sector`
    """
    if name == "sources_tcestats_single_sector":
        return _get_sources_tcestats_single_sector()
    elif name == "sources_tcestats_multi_sector":
        return _get_sources_tcestats_multi_sector()
    elif name == "sources_dv_sh_single_sector":
        return _get_sources_dv_sh_single_sector()
    elif name == "sources_dv_sh_multi_sector":
        return _get_sources_dv_sh_multi_sector()

    #  case unhandled attributes
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def _get_sources_from_file():
    fp = open(f"{DATA_BASE_DIR}/{SOURCE_URLS_FILENAME}", "r")  # somehow with open("...") as f does not work
    config = json.load(fp)
    fp.close()
    return config


def _get_sources_tcestats_single_sector():
    return _get_sources_from_file()["sources_tcestats_single_sector"]


def _get_sources_tcestats_multi_sector():
    return _get_sources_from_file()["sources_tcestats_multi_sector"]


def _get_sources_dv_sh_single_sector():
    # DV sh files followed a consistent pattern based on sector
    def sector(url):
        # get sector number from CSV URL, without padded zeros
        return re.search(r"tess\d+-s0*(\d+)", url)[1]

    def dv_url(sector):
        return f"https://archive.stsci.edu/missions/tess/download_scripts/sector/tesscurl_sector_{sector}_dv.sh"

    return [dv_url(sector(url)) for url in _get_sources_tcestats_single_sector()]


def _get_sources_dv_sh_multi_sector():
    # DV sh files followed a consistent pattern based on sector
    def sector(url):
        # get string number from CSV URL, e.g., s0001-s0096
        return re.search(r"tess\d+-([s0-9-]+)_dvr", url)[1]

    def dv_url(sector):
        return f"https://archive.stsci.edu/missions/tess/download_scripts/sector/tesscurl_multisector_{sector}_dv.sh"

    return [dv_url(sector(url)) for url in _get_sources_tcestats_multi_sector()]


def extract_source_urls_from_mast():
    """Extract source URLs (CSVs) from MAST webpage."""
    base_url = "https://archive.stsci.edu"
    url = "https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_tce.html"
    # url = "https://web.archive.org/web/20260215203338/https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_tce.html"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.select("table")[4]  # DV single sector
    links = table.select("tr td:nth-of-type(3) a")
    urls_single_sector = [base_url + a.get("href") for a in links]
    urls_single_sector.reverse()  # make it chronological starting from sector 1

    table = soup.select("table")[5]  # DV multi sector
    links = table.select("tr td:nth-of-type(3) a")
    urls_multi_sector = [base_url + a.get("href") for a in links]
    urls_multi_sector.reverse()  # make it chronological starting from sector 1

    return {
        "sources_tcestats_single_sector": urls_single_sector,
        "sources_tcestats_multi_sector": urls_multi_sector,
    }


def extract_and_save_source_urls_to_file():
    source_urls_cfg = extract_source_urls_from_mast()
    with open(f"{DATA_BASE_DIR}/{SOURCE_URLS_FILENAME}", "w", encoding="utf-8") as dest:
        json.dump(source_urls_cfg, dest, indent=4)
