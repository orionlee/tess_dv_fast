Stripped down sample data for unit tests.


## TIC 261136679

- multiple average case single-sector (chosen S1, S95 ), multi-sector TCEs (s1-9, s1-96)
  -  s95 and s1-s96 have  the new joint centroid offset columns, e.g., tce_ditco_jsky

```shell
ls data/tess_dv_fast/tess*s0001-s0001*.csv

cat data/tess_dv_fast/tess*s0001-s0001*.csv | head -8

# headers and 1 row  
cat data/tess_dv_fast/tess*s0001-s0001*.csv | head -8 > tests/data/tess_dv_fast/tess2018206190142-s0001-s0001_dvr-tcestats.csv

# the target row(s)
cat data/tess_dv_fast/tess*s0001-s0001*.csv | grep 261136679 >> tests/data/tess_dv_fast/tess2018206190142-s0001-s0001_dvr-tcestats.csv

# another 3 random rows
cat data/tess_dv_fast/tess*s0001-s0001*.csv | tail -3 >> tests/data/tess_dv_fast/tess2018206190142-s0001-s0001_dvr-tcestats.csv

# verify the results
tail -6 tests/data/tess_dv_fast/tess2018206190142-s0001-s0001_dvr-tcestats.csv

# the correspond DV sh 
head -1 data/tess_dv_fast/tesscurl_sector_1_dv.sh  > tests/data//tess_dv_fast/tesscurl_sector_1_dv.sh
cat tests/data/tess_dv_fast/tess2018206190142-s0001-s0001_dvr-tcestats.csv | egrep -v '#|tce' | cut -d ',' -f 2 | xargs -i grep {}  data/tess_dv_fast/tesscurl_sector_1_dv.sh >> tests/data/tess_dv_fast/tesscurl_sector_1_dv.sh

# ---

ls data/tess_dv_fast/tess*s0095-s0095*.csv

cat data/tess_dv_fast/tess*s0095-s0095*.csv | head -8

# headers and 1 row  
cat data/tess_dv_fast/tess*s0095-s0095*.csv | head -8 > tests/data/tess_dv_fast/tess2025206194924-s0095-s0095_dvr-tcestats.csv

# the target row(s)
cat data/tess_dv_fast/tess*s0095-s0095*.csv | grep 261136679 >> tests/data/tess_dv_fast/tess2025206194924-s0095-s0095_dvr-tcestats.csv

# another 3 random rows
cat data/tess_dv_fast/tess*s0095-s0095*.csv | tail -3 >> tests/data/tess_dv_fast/tess2025206194924-s0095-s0095_dvr-tcestats.csv

# verify the results
tail -6 tests/data/tess_dv_fast/tess2025206194924-s0095-s0095_dvr-tcestats.csv

# the correspond DV sh 
head -1 data/tess_dv_fast/tesscurl_sector_95_dv.sh  > tests/data//tess_dv_fast/tesscurl_sector_95_dv.sh
cat tests/data/tess_dv_fast/tess2025206194924-s0095-s0095_dvr-tcestats.csv | egrep -v '#|tce' | cut -d ',' -f 2 | xargs -i grep {}  data/tess_dv_fast/tesscurl_sector_95_dv.sh >> tests/data/tess_dv_fast/tesscurl_sector_95_dv.sh

# ---

ls data/tess_dv_fast/tess*s0001-s0009*.csv

cat data/tess_dv_fast/tess*s0001-s0009*.csv | head -8

# headers and 1 row  
cat data/tess_dv_fast/tess*s0001-s0009*.csv | head -8 > tests/data/tess_dv_fast/tess2018206190142-s0001-s0009_dvr-tcestats.csv

# the target row(s)
cat data/tess_dv_fast/tess*s0001-s0009*.csv | grep 261136679 >> tests/data/tess_dv_fast/tess2018206190142-s0001-s0009_dvr-tcestats.csv

# another 3 random rows
cat data/tess_dv_fast/tess*s0001-s0009*.csv | tail -3 >> tests/data/tess_dv_fast/tess2018206190142-s0001-s0009_dvr-tcestats.csv

# verify the results
tail -6 tests/data/tess_dv_fast/tess2018206190142-s0001-s0009_dvr-tcestats.csv

# the correspond DV sh 
head -1 data/tess_dv_fast/tesscurl_multisector_s0001-s0009_dv.sh  > tests/data//tess_dv_fast/tesscurl_multisector_s0001-s0009_dv.sh
cat tests/data/tess_dv_fast/tess2018206190142-s0001-s0009_dvr-tcestats.csv | egrep -v '#|tce' | cut -d ',' -f 2 | xargs -i grep {}  data/tess_dv_fast/tesscurl_multisector_s0001-s0009_dv.sh >> tests/data/tess_dv_fast/tesscurl_multisector_s0001-s0009_dv.sh

# ---

ls data/tess_dv_fast/tess*s0001-s0096*.csv

cat data/tess_dv_fast/tess*s0001-s0096*.csv | head -8

# headers and 1 row  
cat data/tess_dv_fast/tess*s0001-s0096*.csv | head -8 > tests/data/tess_dv_fast/tess2018206190142-s0001-s0096_dvr-tcestats.csv

# the target row(s)
cat data/tess_dv_fast/tess*s0001-s0096*.csv | grep 261136679 >> tests/data/tess_dv_fast/tess2018206190142-s0001-s0096_dvr-tcestats.csv

# another 3 random rows
cat data/tess_dv_fast/tess*s0001-s0096*.csv | tail -3 >> tests/data/tess_dv_fast/tess2018206190142-s0001-s0096_dvr-tcestats.csv

# verify the results
tail -6 tests/data/tess_dv_fast/tess2018206190142-s0001-s0096_dvr-tcestats.csv

```
