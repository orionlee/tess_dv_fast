from pathlib import Path
from importlib import reload

from numpy.testing import assert_equal, assert_almost_equal
import pytest

from tess_dv_fast import tess_dv_fast_spec, tess_dv_fast_build, tess_dv_fast

@pytest.fixture(scope="module", autouse=True)
def spec_for_test():
    """Use a patched tess_dv_fast_spec module for unit tests """

    # --- SETUP  ---

    # the data dir is tests specific
    tess_dv_fast_spec.DATA_BASE_DIR = str((Path(__file__).parent / "data" / "tess_dv_fast").resolve())

    # use a subset of the data, the csv/sh have been pre-downloaded and trimmed for the use  of unit tests
    tess_dv_fast_spec.sources_tcestats_single_sector = [
        "https://archive.stsci.edu/missions/tess/catalogs/tce/tess2018206190142-s0001-s0001_dvr-tcestats.csv",
        "https://archive.stsci.edu/missions/tess/catalogs/tce/tess2025206194924-s0095-s0095_dvr-tcestats.csv",
    ]

    tess_dv_fast_spec.sources_dv_sh_single_sector = [
        "https://archive.stsci.edu/missions/tess/download_scripts/sector/tesscurl_sector_1_dv.sh",
        "https://archive.stsci.edu/missions/tess/download_scripts/sector/tesscurl_sector_95_dv.sh",
    ]

    tess_dv_fast_spec.sources_tcestats_multi_sector = [
        "https://archive.stsci.edu/missions/tess/catalogs/tce/tess2018206190142-s0001-s0009_dvr-tcestats.csv",
        "https://archive.stsci.edu/missions/tess/catalogs/tce/tess2018206190142-s0001-s0096_dvr-tcestats.csv",
    ]

    tess_dv_fast_spec.sources_dv_sh_multi_sector = [
        "https://archive.stsci.edu/missions/tess/download_scripts/sector/tesscurl_multisector_s0001-s0009_dv.sh",
        "https://archive.stsci.edu/missions/tess/download_scripts/sector/tesscurl_multisector_s0001-s0096_dv.sh",
    ]

    # force the modules to use the patched spec module
    reload(tess_dv_fast_build)
    reload(tess_dv_fast)

    yield

    # --- TEARDOWN  ---
    # restore the original modules
    reload(tess_dv_fast_spec)
    reload(tess_dv_fast_build)
    reload(tess_dv_fast)


def _build_test_db(minimal_db):
    # we are not actually testing the download
    # the tests/data/tess_dv_fast has test-specific versions of the csv
    tess_dv_fast_build.download_all_data()
    tess_dv_fast_build._export_tcestats_as_db(minimal_db=minimal_db)


def assert_tic_offsets(df,
    expected_TicOffset_rm,  # the classic TicOffset
    expected_TicOffset_jnt, # the new TIcOffset from joint difference images
    expected_TicOffset_display,  # the value to be shown in UI
    decimal=1,
):
    assert_almost_equal(df["tce_ditco_msky"].iloc[0], expected_TicOffset_rm, decimal=decimal)

    assert_almost_equal(df["tce_ditco_jsky"].iloc[0], expected_TicOffset_jnt, decimal=decimal)

    _df_display = tess_dv_fast.display_tce_infos(df, return_as="df")
    # the value to be displayed (it's encoded as a <offset>|<offset_error> string)
    actual_TicOffset = float(_df_display["TicOffset"].iloc[0].split('|')[0])
    assert_almost_equal(actual_TicOffset, expected_TicOffset_display, decimal=decimal)


@pytest.mark.parametrize("minimal_db", [True, False])
def test_build_query(minimal_db):
    _build_test_db(minimal_db=minimal_db)

    df = tess_dv_fast.get_tce_infos_of_tic(261136679)  # pi Men

    # 1 TCE for each single sector, 2 TCEs for each multi-sector
    assert_equal(len(df), 6, "expected number of TCEs for pi Men in test data")

    # use  s0001-s0096
    _df = df[df["exomast_id"] == "TIC261136679S0001S0096TCE1"]
    assert_tic_offsets(_df, 20.8, 24.5, 24.5)

    # use  s0001-s0001
    _df = df[df["exomast_id"] == "TIC261136679S0001S0001TCE1"]
    assert_tic_offsets(_df, 40.5, 0.0, 40.5)  # no TicOffset-jnt in single sector
