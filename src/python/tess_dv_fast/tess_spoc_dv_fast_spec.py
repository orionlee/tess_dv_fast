"""TESS-SPOC TCE data specifications and source URLs."""

import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_BASE_PATH = os.environ.get("TESS_DB_BASE_PATH", "./")
DATA_BASE_DIR = str((Path(_BASE_PATH) / "data" / "tess_dv_fast").resolve())

TCESTATS_FILENAME = "tess_spoc_tcestats.csv"
TCESTATS_DBNAME = "tess_spoc_tcestats.db"
SOURCE_URLS_FILENAME = "tess_spoc_dv_fast_spec.json"


# Sources at: https://archive.stsci.edu/hlsp/tess-spoc

sources_dv_sh_single_sector = [
    (
        "https://archive.stsci.edu/hlsps/tess-spoc/download_scripts/"
        f"hlsp_tess-spoc_tess_phot_s{sec:04d}_tess_v1_dl-dv.sh"
    )
    for sec in range(36, 85 + 1)
]


sources_dv_sh_multi_sector = [
    # the `s0056-s0069` appears to be mis-named. The content represents s0036-s0069
    "https://archive.stsci.edu/hlsps/tess-spoc/download_scripts/hlsp_tess-spoc_tess_phot_s0056-s0069_tess_v1_dl-dv.sh",
]

# sh source: https://archive.stsci.edu/hlsp/tess-spoc
def __getattr__(name: str):
    """Provide attributes `sources_dv_sh_single_sector`, `sources_dv_sh_multi_sector`
    """
    if name == "sources_dv_sh_single_sector":
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


def _get_sources_dv_sh_single_sector():
    return _get_sources_from_file()["sources_dv_sh_single_sector"]


def _get_sources_dv_sh_multi_sector():
    return _get_sources_from_file()["sources_dv_sh_multi_sector"]


def extract_source_urls_from_mast():
    """Extract source URLs (CSVs) from MAST webpage."""
    url = "https://archive.stsci.edu/hlsp/tess-spoc"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    # single-sector DVs: in the format of link for LC | TP | DV
    links = soup.select("table tr td  a:nth-of-type(3)")
    urls_single_sector = [a.get("href") for a in links if a.text == 'DV']  # filter out non-DV link (before sector 36)
    urls_single_sector.sort()

    # Multi-sector DVs
    #  searching the last section, under the heading "Multi-Sector DV Files"
    links = soup.select('h4')[-1].next_sibling.next_sibling.select('table td > a:nth-of-type(1)')
    urls_multi_sector = [a.get("href") for a in links]
    urls_multi_sector.sort()

    return {
        "sources_dv_sh_single_sector": urls_single_sector,
        "sources_dv_sh_multi_sector": urls_multi_sector,
    }


def extract_and_save_source_urls_to_file():
    source_urls_cfg = extract_source_urls_from_mast()
    with open(f"{DATA_BASE_DIR}/{SOURCE_URLS_FILENAME}", "w", encoding="utf-8") as dest:
        json.dump(source_urls_cfg, dest, indent=4)
