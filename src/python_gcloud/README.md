# TESS TCEs Webapp for Google Cloud Run

- Contains additional files needed for Google Cloud Run deployment

- Run the following to create a directory at `<project_root>/build` with the necessary files to deploy to Google Cloud Run.

```shell
# at project root
src/python_gcloud/assemble.sh
```


## Miscellaneous Notes

- Google Cloud Run requires entry point to be `main.py` with `app` attribute (of the flask app).
