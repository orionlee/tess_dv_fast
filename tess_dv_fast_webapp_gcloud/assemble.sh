#!/bin/sh

# Assemble TESS TCEs webapp that can be source-deployed to Google Cloud Run
#

base=`dirname $0`
dest=$1
if [ "$dest" == "" ]; then
    dest=$base/../build
fi

# the commit SHA
# - in gcloud continuous deployment env, it will be supplied as a parameter
#   (git not available in gcloud's bash build step)
# - in local build, we generates it locally
commit_sha=$2
if [ "$commit_sha" == "" ]; then
  commit_sha=`git rev-parse HEAD`
  echo To save commit SHA in build: $commit_sha
fi


set -e

mkdir -p $dest

mkdir -p $dest/data/tess_dv_fast
# --update --archive
cp --update --archive  $base/../data/tess_dv_fast/tess_tcestats.db  $dest/data/tess_dv_fast
cp --update --archive  $base/../data/tess_dv_fast/tess_spoc_tcestats.db  $dest/data/tess_dv_fast

cp --update --archive  $base/*  $dest
cp --update --archive  $base/.*  $dest
cp --update --archive  $base/../tess_dv_fast.py $base/../tess_spoc_dv_fast.py $base/../tess_dv_fast_webapp.py  $dest

# save commit SHA to be displayed in the UI.
echo $commit_sha > $dest/build.txt

echo SQLite database included in the deployment:
ls -l $dest/data/tess_dv_fast/tess*_tcestats.db

echo
echo Sources assembled. You can do the following for actual deployment:
echo
echo cd $dest
echo "# sanity test locally"
echo python main.py
echo "# actual deployment with Google Cloud SDK"
echo gcloud run deploy --source .
