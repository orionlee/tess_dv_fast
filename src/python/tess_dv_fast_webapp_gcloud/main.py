import os

from tess_dv_fast import tess_dv_fast_webapp

#
# Entrypoint for Google Cloud Run deployment
#
app = tess_dv_fast_webapp.app  # Google Cloud Run requires `app` attribute in main
if __name__ == "__main__":  # for local testing only. not used by GCR
    app.run(
        debug=False,
        use_reloader=False,  # disable hot reload and avoid the extra watcher process
        use_evalex=False,  # disable werkzeug's web-based  interactive debugger on error page
        host=os.environ.get("TESS_TCES_HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8080)),
    )
