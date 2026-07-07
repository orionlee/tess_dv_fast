"""tess_dv_fast package."""

from importlib.metadata import PackageNotFoundError, version

from . import tess_dv_fast
from . import tess_dv_fast_spec
from . import tess_spoc_dv_fast
from . import tess_spoc_dv_fast_spec

try:
    __version__ = version("tess-dv-fast")
except PackageNotFoundError:  # pragma: no cover - local source checkout
    __version__ = "0.0.0-dev"  # Fallback for local, uninstalled development

__all__ = [
    "__version__",
    "tess_dv_fast",
    "tess_dv_fast_spec",
    "tess_spoc_dv_fast",
    "tess_spoc_dv_fast_spec",
]
