package spec

import (
	"path/filepath"
	"regexp"
)

// SPOC data specifications (2-minute cadence)
const (
	DataBaseDirName  = "data/tess_dv_fast"
	TCEStatsFilename = "tess_tcestats.csv"
	TCEStatsDBName   = "tess_tcestats.db"
	TCEStatsTable    = "tess_tcestats"
)

// TESS-SPOC data specifications (Full-Frame Image)
const (
	TessSpocFilename = "tess_spoc_tcestats.csv"
	TessSpocDBName   = "tess_spoc_tcestats.db"
	TessSpocTable    = "tess_spoc_tcestats"
)

var (
	// These will be populated on init
	DatabaseDir string
)

// High watermarks info
type HighWatermarks struct {
	SpocSingleSector   string `json:"single_sector"`
	SpocMultiSector    string `json:"multi_sector"`
	TessSpocSingleSector string `json:"tess_spoc_single_sector"`
	TessSpocMultiSector string `json:"tess_spoc_multi_sector"`
}

// Go version doesn't really need the sources, relying on on the sqlite db created by Python version
// We keep the latest one to support GetHighWatermarks() , however.

// TCE stats CSV sources (single sector)
var TCEStatsSingleSectorSources = []string{
	// ... (truncated, only the latest one is here)
	"https://archive.stsci.edu/missions/tess/catalogs/tce/tess2025258033922-s0097-s0097_dvr-tcestats.csv",
}

// TCE stats CSV sources (multi sector)
var TCEStatsMultiSectorSources = []string{
	// ... (truncated, only the latest one is here)
	"https://archive.stsci.edu/missions/tess/catalogs/tce/tess2018206190142-s0001-s0092_dvr-tcestats.csv",
}

// TESS-SPOC TCE sources
var TessSpocSingleSectorSources = []string{
	// ... (truncated, only the latest ones are here)
	"https://archive.stsci.edu/hlsps/tess-spoc/download_scripts/hlsp_tess-spoc_tess_phot_s0077_tess_v1_dl-dv.sh",
}

// TESS-SPOC TCE sources, multi-sector
var TessSpocMultiSectorSources = []string{
	// ... (truncated, only the latest ones are here)
	"https://archive.stsci.edu/hlsps/tess-spoc/download_scripts/hlsp_tess-spoc_tess_phot_s0056-s0069_tess_v1_dl-dv.sh",
}

// GetHighWatermarks extracts the latest sector information from sources
func GetHighWatermarks() *HighWatermarks {
	hw := &HighWatermarks{}

	if len(TCEStatsSingleSectorSources) > 0 {
		re := regexp.MustCompile(`(s\d+)_dvr-tcestats`)
		if matches := re.FindStringSubmatch(TCEStatsSingleSectorSources[len(TCEStatsSingleSectorSources)-1]); len(matches) > 1 {
			hw.SpocSingleSector = matches[1]
		}
	}

	if len(TCEStatsMultiSectorSources) > 0 {
		re := regexp.MustCompile(`(s\d+-s\d+)_dvr-tcestats`)
		if matches := re.FindStringSubmatch(TCEStatsMultiSectorSources[len(TCEStatsMultiSectorSources)-1]); len(matches) > 1 {
			hw.SpocMultiSector = matches[1]
		}
	}

	if len(TessSpocSingleSectorSources) > 0 {
		re := regexp.MustCompile(`(s\d+)_tess_v1_dl-dv`)
		if matches := re.FindStringSubmatch(TessSpocSingleSectorSources[len(TessSpocSingleSectorSources)-1]); len(matches) > 1 {
			hw.TessSpocSingleSector = matches[1]
		}
	}

	if len(TessSpocMultiSectorSources) > 0 {
		re := regexp.MustCompile(`(s\d+-s\d+)_tess_v1_dl-dv`)
		if matches := re.FindStringSubmatch(TessSpocMultiSectorSources[len(TessSpocMultiSectorSources)-1]); len(matches) > 1 {
			hw.TessSpocMultiSector = matches[1]
		}
	}
	return hw
}

// InitDatabaseDir sets the database directory relative to the given base path
func InitDatabaseDir(basePath string) {
	DatabaseDir = filepath.Join(basePath, DataBaseDirName)
}
