#!/bin/sh

# Assemble TESS TCEs webapp that can be source-deployed to Google Cloud Run
#

base=`dirname $0`
dest=$1

if [ "$dest" == "" ]; then
    dest=$base/../build
fi

set -e

mkdir -p $dest

mkdir -p $dest/data/tess_dv_fast
# --update --archive
cp --update --archive  $base/../data/tess_dv_fast/tess_tcestats.db  $dest/data/tess_dv_fast

cp --update --archive  $base/*  $dest
cp --update --archive  $base/.*  $dest
cp --update --archive  $base/../tess_dv_fast.py $base/../tess_dv_fast_webapp.py  $dest

echo SQLite database included in the deployment:
ls -l $dest/data/tess_dv_fast/tess_tcestats.db

echo
echo Sources assembled. You can do the following for actual deployment:
echo
echo cd $dest
echo "# sanity test locally"
echo python main.py
echo "# actual deployment with Google Cloud SDK"
echo gcloud run deploy --source .
