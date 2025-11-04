from flask import Flask
from flask import request, redirect, url_for

import tess_dv_fast  # standard SPOC TCEs
import tess_spoc_dv_fast  # HLSP TESS-SPOC TCEs


app = Flask(__name__)


@app.route('/')
def index():
    return redirect(url_for('tces'))


@app.route("/tces")
def tces():
    tic = request.args.get("tic", None)

    # case return search form
    if tic is None:
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
        }
        </style>
        <form>
            TIC: <input name="tic" type="number" placeholder="TIC id, e.g., 261136679"></input>
            <input type="Submit"></input>
        </form>
        <footer style="margin-top: 5vh; font-size: 85%;">
            Based on data published by <a href="https://archive.stsci.edu/" target="_blank">MAST</a>:
            <ul>
                <li><a href="https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_tce.html" target="_blank">TCE statistics bulk downloads</a> (<code>csv</code> files)</li>
                <li><a href="https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_ffi-tp-lc-dv.html#:~:text=Data-,Validation,-%2D%20Single%20Sector" target="_blank">TESS DV files bulk downloads</a> (<code>sh</code> files)</li>
            </ul>
"""
        high_watermarks = tess_dv_fast.get_high_watermarks()
        return most_of_html + f"""
            Latest:
            <ul>
                <li>Single sector: {high_watermarks["single_sector"]}</li>
                <li>Multi sector: {high_watermarks["multi_sector"]}</li>
            </ul>
            <br>
            <a href="https://github.com/orionlee/tess_dv_fast/" target="_blank">Sources /Issues</a>
        </footer>
    </body>
</html>
"""

    # case do actual search by tic
    df = tess_dv_fast.get_tce_infos_of_tic(tic)
    spoc_content = tess_dv_fast.display_tce_infos(df, return_as="html", no_tce_html="No SPOC TCE")
    # make table searchable / sortable by https://github.com/javve/list.js
    spoc_content = spoc_content.replace("<tbody", '<tbody class="list"')
    for i in [0, 4, 5, 6, 7, 8, 9, 10, 11]:
        spoc_content = spoc_content.replace(
            f'class="col_heading level0 col{i}"',
            f'class="col_heading level0 col{i} sort" data-sort="col{i}"'
            )

    res_css = r"""
<style type="text/css">
body {
    margin-left: 16px;
}

footer {
    margin-bottom: 16px;
}

h1 a {
    text-decoration: none;
}

h2 { /* make sub header for TESS-SPOC smaller */
    font-size: 1.2 rem;
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

    # TESS-SPOC
    df_tess_spoc = tess_spoc_dv_fast.get_tce_infos_of_tic(tic)
    if len(df_tess_spoc) > 0:
        tess_spoc_content = tess_spoc_dv_fast.display_tce_infos(df_tess_spoc, return_as="html")
        tess_spoc_content = f"<hr><h2>TESS-SPOC TCEs</h2>\n{tess_spoc_content}"
    else:  # no TESS-SPOC results, don't show anything
        tess_spoc_content = ""

    res = f"""\
<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="data:,">
        <title>({len(df)}) TCEs for TIC {tic}</title>
    </head>
    <body>
        <div id="result">
            <h1>TCEs for TIC <a href="https://exofop.ipac.caltech.edu/tess/target.php?id={tic}" target="_exofop">{tic}</a>
            <input class="search" placeholder="Search table" style="margin-left: 40ch;" accesskey="/">
            </h1>
            {spoc_content}
            {tess_spoc_content}
        </div>

        <hr>
        <footer>
            <a href="/tces">New Search</a>
        </footer>

        <script src="https://cdn.jsdelivr.net/gh/javve/list.js@2.3.1/dist/list.min.js"></script>
        <script>
            if (document.querySelector('#result table')) {{
                // init search/sort only if there is a result table
                const options = {{valueNames: ['col0', 'col4', 'col5', 'col6', 'col7', 'col8', 'col9', 'col10', 'col11']}};
                const tceList = new List('result', options);
            }}
        </script>
        {res_css}
    </body>
</html>
"""

    return res
