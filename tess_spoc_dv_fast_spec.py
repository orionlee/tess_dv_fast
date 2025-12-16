"""TESS-SPOC TCE data specifications and source URLs."""

from pathlib import Path
import re

DATA_BASE_DIR = f"{Path(__file__).parent}/data/tess_dv_fast"

TCESTATS_FILENAME = "tess_spoc_tcestats.csv"
TCESTATS_DBNAME = "tess_spoc_tcestats.db"


# Sources at: https://archive.stsci.edu/hlsp/tess-spoc

sources_dv_sh_single_sector = [
    ("https://archive.stsci.edu/hlsps/tess-spoc/download_scripts/"
     f"hlsp_tess-spoc_tess_phot_s{sec:04d}_tess_v1_dl-dv.sh") for sec in range(36, 79 + 1)
]


sources_dv_sh_multi_sector = [
    # the `s0056-s0069` appears to be mis-named. The content represents s0036-s0069
    "https://archive.stsci.edu/hlsps/tess-spoc/download_scripts/hlsp_tess-spoc_tess_phot_s0056-s0069_tess_v1_dl-dv.sh",

]


def get_high_watermarks():

    latest_single_sector_url = sources_dv_sh_single_sector[-1]
    latest_single_sector_match = re.search(r"(s\d+)", latest_single_sector_url)
    if latest_single_sector_match is not None:
        latest_single_sector = latest_single_sector_match[1]

    latest_multi_sector_url = sources_dv_sh_multi_sector[-1]
    latest_multi_sector_match = re.search(r"(s\d+-s\d+)", latest_multi_sector_url)
    if latest_multi_sector_match is not None:
        latest_multi_sector = latest_multi_sector_match[1]

    return dict(single_sector=latest_single_sector, multi_sector=latest_multi_sector)
