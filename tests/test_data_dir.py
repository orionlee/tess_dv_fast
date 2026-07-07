import importlib
import os


def _reload_spec_module(monkeypatch, tmp_path, env_value=None):
    monkeypatch.chdir(tmp_path)
    if env_value is None:
        monkeypatch.delenv("TESS_DB_BASE_PATH", raising=False)
    else:
        monkeypatch.setenv("TESS_DB_BASE_PATH", env_value)

    import tess_dv_fast.tess_dv_fast_spec as spec_module

    return importlib.reload(spec_module)


def test_default_data_base_dir_is_relative_to_cwd(monkeypatch, tmp_path):
    spec_module = _reload_spec_module(monkeypatch, tmp_path)

    expected = str((tmp_path / "data" / "tess_dv_fast").resolve())
    assert spec_module.DATA_BASE_DIR == expected


def test_env_override_sets_data_base_dir(monkeypatch, tmp_path):
    custom_base = tmp_path / "custom-base"
    spec_module = _reload_spec_module(monkeypatch, tmp_path, env_value=str(custom_base))

    expected = str((custom_base / "data" / "tess_dv_fast").resolve())
    assert spec_module.DATA_BASE_DIR == expected
