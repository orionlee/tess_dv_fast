package spec

import (
	"path/filepath"
	"regexp"
)

// SPOC data specifications
const (
	DataBaseDirName  = "data/tess_dv_fast"
	TCEStatsFilename = "tess_tcestats.csv"
	TCEStatsDBName   = "tess_tcestats.db"
)

var (
	// These will be populated on init
	DatabaseDir string
)

// High watermarks info
type HighWatermarks struct {
	SingleSector string `json:"single_sector"`
	MultiSector  string `json:"multi_sector"`
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

// GetHighWatermarks extracts the latest sector information from sources
func GetHighWatermarks() *HighWatermarks {
	hw := &HighWatermarks{}

	if len(TCEStatsSingleSectorSources) > 0 {
		re := regexp.MustCompile(`(s\d+)_dvr-tcestats`)
		if matches := re.FindStringSubmatch(TCEStatsSingleSectorSources[len(TCEStatsSingleSectorSources)-1]); len(matches) > 1 {
			hw.SingleSector = matches[1]
		}
	}

	if len(TCEStatsMultiSectorSources) > 0 {
		re := regexp.MustCompile(`(s\d+-s\d+)_dvr-tcestats`)
		if matches := re.FindStringSubmatch(TCEStatsMultiSectorSources[len(TCEStatsMultiSectorSources)-1]); len(matches) > 1 {
			hw.MultiSector = matches[1]
		}
	}

	return hw
}

// InitDatabaseDir sets the database directory relative to the given base path
func InitDatabaseDir(basePath string) {
	DatabaseDir = filepath.Join(basePath, DataBaseDirName)
}
