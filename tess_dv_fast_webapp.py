from flask import Flask
from flask import request, redirect, url_for

import tess_dv_fast


app = Flask(__name__)


@app.route('/')
def index():
    return redirect(url_for('tces'))


@app.route("/tces")
def tces():
    tic = request.args.get("tic", None)

    if tic is None:
        return """\
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
        </footer>
    </body>
</html>
"""

    # do actual search by tic
    df = tess_dv_fast.get_tce_infos_of_tic(tic)
    res_content = tess_dv_fast.display_tce_infos(df, return_as="html", no_tce_html="No TCE")
    res_content = res_content.replace("<table", '<table class="sortable"')

    res_css = """\
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
    text-transform: initial !important;  /* override sortable style */
}

th, td {
    padding: 0.25rem;
    padding-bottom: 0.5rem;
}

tbody tr:nth-child(even) {
    background-color: #f5f5f5
}
</style>
"""

    res = f"""\
<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="data:,">
        <title>({len(df)}) TCEs for TIC {tic}</title>
    </head>
    <body>
        <h1>TCEs for TIC <a href="https://exofop.ipac.caltech.edu/tess/target.php?id={tic}" target="_exofop">{tic}</a></h1>
        <div id="result">
        {res_content}
        </div>

        <hr>
        <footer>
            <a href="/tces">New Search</a>
        </footer>

        <link href="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@latest/sortable.min.css" rel="stylesheet" />
        <script src="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@latest/sortable.min.js"></script>
        {res_css}
    </body>
</html>
"""

    return res
