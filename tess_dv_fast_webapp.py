from functools import cache
import logging
import re

from flask import Flask
from flask import request
from markupsafe import escape

import tess_dv_fast  # standard SPOC TCEs
import tess_dv_fast_spec
import tess_spoc_dv_fast  # HLSP TESS-SPOC TCEs
import tess_spoc_dv_fast_spec


app = Flask(__name__)
log = logging.getLogger(__name__)

# Configuration constants
SPOC_SORTABLE_COLUMNS = [0, 4, 5, 6, 7, 8, 9, 10, 11]
SPOC_TABLE_ID = "table_spoc"
TESS_SPOC_TABLE_ID = "table_tess_spoc"
EXOFOP_BASE_URL = "https://exofop.ipac.caltech.edu/tess/target.php"


@cache
def get_build_sha():
    from pathlib import Path

    build_fname = Path(__file__).parent / "build.txt"
    try:
        with build_fname.open() as f:
            return f.readline().strip()
    except FileNotFoundError:
        # in dev mode from source, build.txt is not generated
        return ""
    except Exception as e:
        log.error(f"get_build_sha(): Unexpected error, return empty string. {e}")
        return ""


def get_build_sha_short():
    return get_build_sha()[:8]


def _render_home():
    most_of_html = """\
<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="data:,">
        <title>Search TESS TCEs</title>
    </head>
    <body>
        <h1>Search TESS TCEs</h1>
        <style type="text/css">
        body {
            margin-left: 16px;
            font-family: sans-serif;
        }
        </style>
        <form>
            TIC: <input name="tic" type="number" placeholder="TIC id, e.g., 261136679"></input>
            <input type="Submit"></input>
        </form>
"""
    spoc_high_watermarks = tess_dv_fast_spec.get_high_watermarks()
    tess_spoc_high_watermarks = tess_spoc_dv_fast_spec.get_high_watermarks()
    return most_of_html + f"""
        <footer style="margin-top: 5vh; font-size: 85%;">
            <p>SPOC (2 min cadence): based on data published by <a href="https://archive.stsci.edu/" target="_blank">MAST</a>:</p>
            <ul>
                <li><a href="https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_tce.html" target="_blank">TCE statistics bulk downloads</a> (<code>csv</code> files)</li>
                <li><a href="https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_ffi-tp-lc-dv.html#:~:text=Data-,Validation,-%2D%20Single%20Sector" target="_blank">TESS DV files bulk downloads</a> (<code>sh</code> files)</li>
            </ul>
            Latest:
            <ul>
                <li>Single sector: {spoc_high_watermarks["single_sector"]}</li>
                <li>Multi sector: {spoc_high_watermarks["multi_sector"]}</li>
            </ul>
            <p>TESS-SPOC (FFI): based on data published by <a href="https://archive.stsci.edu/hlsp/tess-spoc" target="_blank">HLSP</a> at MAST:</p>
            Latest:
            <ul>
                <li>Single sector: {tess_spoc_high_watermarks["single_sector"]}</li>
                <li>Multi sector: {tess_spoc_high_watermarks["multi_sector"]}</li>
            </ul>

            <br>
            <a href="https://github.com/orionlee/tess_dv_fast/" target="_blank">Sources /Issues</a><br>
            Build:
            <a target="_blank" href="https://github.com/orionlee/tess_dv_fast/commit/{get_build_sha()}"
                >{get_build_sha_short()}</a><br>
        </footer>
    </body>
</html>
"""


def _apply_table_styling(content: str, table_id: str, sortable_cols: list = None) -> str:
    """Apply standard table styling and sorting to rendered content.

    Args:
        content: HTML content from display_tce_infos()
        table_id: ID to assign to the table
        sortable_cols: List of column indices to make sortable

    Returns:
        Styled HTML content
    """
    # custom id for the table for javascript functions
    content = re.sub('<table id="[^"]+"', f'<table id="{table_id}"', content)

    if sortable_cols:
        # make table searchable / sortable by https://github.com/javve/list.js
        content = content.replace("<tbody", '<tbody class="list"')
        for i in sortable_cols:
            content = content.replace(
                f'class="col_heading level0 col{i}"',
                f'class="col_heading level0 col{i} sort" data-sort="col{i}"'
            )

    return content


def _render_spoc_content(df_spoc):
    """Render SPOC TCE content as HTML.

    Returns:
        HTML content string
    """
    spoc_content = tess_dv_fast.display_tce_infos(df_spoc, return_as="html", no_tce_html="No SPOC TCE")
    spoc_content = _apply_table_styling(spoc_content, SPOC_TABLE_ID, SPOC_SORTABLE_COLUMNS)
    return spoc_content


def _render_tess_spoc_content(df_tess_spoc):
    """Render TESS-SPOC TCE content as HTML.

    Returns:
        HTML content with TESS-SPOC table and duplicate-hiding controls
    """
    if len(df_tess_spoc) < 1:
        # no TESS-SPOC: render nothing
        return ""

    # case have TESS-SPOC content
    tess_spoc_content = tess_spoc_dv_fast.display_tce_infos(df_tess_spoc, return_as="html")
    tess_spoc_content = _apply_table_styling(tess_spoc_content, TESS_SPOC_TABLE_ID)

    tess_spoc_content = f"""
<hr>
<h2>TESS-SPOC TCEs</h2>
<div id="tessSpocDupCtr">
  <span id="tessSpocDupMsg"></span>
  <button id="hideShowInSpocCtl" onclick="document.body.classList.toggle('show_in_spoc');"></button>
</div>
{tess_spoc_content}
"""
    return tess_spoc_content

def _render_error(error_msg: str, status_code: int = 400) -> tuple:
    """Render error page with given message and status code.

    Args:
        error_msg: Error message to display
        status_code: HTTP status code

    Returns:
        Tuple of (HTML content, status code)
    """
    return (
        f"""\
<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="data:,">
        <title>Error - Search TESS TCEs</title>
        <style type="text/css">
            body {{
                margin-left: 16px;
                font-family: sans-serif;
            }}
            .error {{
                color: #d32f2f;
                border: 1px solid #d32f2f;
                padding: 12px;
                border-radius: 4px;
                background-color: #ffebee;
            }}
        </style>
    </head>
    <body>
        <h1>Search TESS TCEs</h1>
        <div class="error">
            <strong>Error:</strong> {escape(error_msg)}
        </div>
        <p><a href="/tces">Back to search</a></p>
    </body>
</html>
""",
        status_code,
    )


@app.route("/tces")
def tces():
    """Main search endpoint for TESS TCEs."""
    tic = request.args.get("tic", None)

    # case return search form
    if tic is None:
        return _render_home()

    # Validate TIC input
    tic = tic.strip() if isinstance(tic, str) else tic
    if not tic:
        return _render_error("TIC cannot be empty.")
    if not re.match(r"^\d+$", tic):
        return _render_error(f"Invalid TIC: {escape(tic)}. Must be a positive integer.")

    # case do actual search by tic
    try:
        df_spoc = tess_dv_fast.get_tce_infos_of_tic(tic)
        df_tess_spoc = tess_spoc_dv_fast.get_tce_infos_of_tic(tic)
    except Exception as e:
        log.exception(f"Query failed for TIC {tic}: {type(e).__name__}: {e}")
        return _render_error(
            f"Database query failed. Please try again later. (Details: {escape(str(e))})",
            status_code=500,
        )

    # Render content
    try:
        spoc_content = _render_spoc_content(df_spoc)
        tess_spoc_content = _render_tess_spoc_content(df_tess_spoc)
    except Exception as e:
        log.error(f"Content rendering failed for TIC {tic}: {type(e).__name__}: {e}")
        return _render_error(
            "Failed to render results. Please try again.",
            status_code=500,
        )

    # Escape TIC for safe display in HTML (XSS protection)
    # - be extra defensive, as it's been validated as a number in earlier codes.
    tic_escaped = escape(tic)
    total_num_tces = len(df_spoc) + len(df_tess_spoc)

    # Log successful query
    log.info(
        f"Query for TIC {tic}: found {len(df_spoc)} SPOC TCEs, {len(df_tess_spoc)} TESS-SPOC TCEs"
    )

    # Generate CSS for styling
    spoc_css = r"""
<style type="text/css">
body {
    margin-left: 16px;
    font-family: sans-serif;
}

footer {
    margin-bottom: 16px;
}

h1 a {
    text-decoration: none;
}

table {
    border-collapse: collapse; /* changed from separate */
    border:none;
    font-size: 0.9rem;
}

thead th {
    position: sticky;
    top: 0; /* for stickiness */
    background-color: darkgray;
    color: white;
}

th, td {
    padding: 5px 10px;
}

tbody tr:nth-child(even) {
    background-color: #f5f5f5
}


/* for sort table */

th.sort {
    cursor: pointer;
}
.sort.asc, .sort.desc {
  color: yellow;
}
.sort.asc::after {
  content: "\025B4";
  padding-left: 3px;
}
.sort.desc::after {
  content: "\025BE";
  padding-left: 3px
}
</style>
"""

    tess_spoc_css = """\
<style type="text/css">
h2 { /* make sub header for TESS-SPOC smaller */
    font-size: 1.2 rem;
}

/* for hide show TESS-SPOC "duplicates" of SPOC */
#tessSpocDupCtr {
    margin-bottom: 6px;
    margin-left: 12px;
    font-size: 80%;
}

tr.in_spoc {
    display: none;
}

.show_in_spoc tr.in_spoc {
    display: table-row;
}

#hideShowInSpocCtl {
    font-size: 80%;
}

#hideShowInSpocCtl::before {
    content: "Show";
}

.show_in_spoc #hideShowInSpocCtl::before {
    content: "Hide";
}
</style>
"""

    # Generate JavaScript for hiding TESS-SPOC duplicates
    tess_spoc_script = r"""
<script>
function addHideShowForTessSpocDupRows() {
    // mark rows (that are "duplicates" of SPOC TCEs) with css class
    const spocTceIds = Array.from(document.querySelectorAll('table#table_spoc tbody td:nth-of-type(1)')).map(td => td.textContent);
    let numInSpoc = 0;
    document.querySelectorAll('table#table_tess_spoc tbody tr').forEach(tr => {
        // TESS-SPOC id generation: SPOC id with '_f' suffix. strip  the suffix for comparison
        const curId = tr.querySelector('td:nth-of-type(1)').textContent.replace('_f', '');
        if (spocTceIds.includes(curId)) {
            tr.classList.add('in_spoc');
            numInSpoc++;
        }
    });
    if (numInSpoc > 0) {
        document.getElementById('tessSpocDupMsg').textContent = `${numInSpoc} TCEs have SPOC counterparts.`;
    } else {
        document.getElementById('tessSpocDupCtr').style.display = 'none';
    }
}
addHideShowForTessSpocDupRows();
</script>
"""

    # assemble the overall result HTML
    return f"""\
<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="data:,">
        <title>({total_num_tces}) TCEs for TIC {tic_escaped}</title>
        {spoc_css}
        {tess_spoc_css}
    </head>
    <body>
        <div id="result">
            <h1>TCEs for TIC <a href="{EXOFOP_BASE_URL}?id={tic_escaped}" target="_exofop">{tic_escaped}</a>
            <input class="search" placeholder="Search table" style="margin-left: 40ch;" accesskey="/">
            </h1>
            {spoc_content}
            {tess_spoc_content}
            {tess_spoc_script if tess_spoc_content else ""}
        </div>

        <hr>
        <footer>
            <a href="/tces">New Search</a>
        </footer>

        <script src="https://cdn.jsdelivr.net/gh/javve/list.js@2.3.1/dist/list.min.js"></script>
        <script>
			// Init in-table sort/filter with list.js for SPOC results (if exists)
            if (document.querySelector('#result table#table_spoc')) {{
                const options = {{valueNames: ['col0', 'col4', 'col5', 'col6', 'col7', 'col8', 'col9', 'col10', 'col11']}};
                const tceList = new List('result', options);
            }}
        </script>
    </body>
</html>
"""
