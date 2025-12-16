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

// TCE stats CSV sources (single sector)
var TCEStatsSingleSectorSources = []string{
	"https://archive.stsci.edu/missions/tess/catalogs/tce/tess2018206190142-s0001-s0001_dvr-tcestats.csv",
	"https://archive.stsci.edu/missions/tess/catalogs/tce/tess2018235142541-s0002-s0002_dvr-tcestats.csv",
	"https://archive.stsci.edu/missions/tess/catalogs/tce/tess2018263124740-s0003-s0003_dvr-tcestats.csv",
	// ... (truncated for brevity, would include all 88+ sectors)
}

// TCE stats CSV sources (multi sector)
var TCEStatsMultiSectorSources = []string{
	"https://archive.stsci.edu/missions/tess/catalogs/tce/tess2024143004541-s0079-s0088_dvr-tcestats.csv",
	// ... (truncated for brevity)
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
