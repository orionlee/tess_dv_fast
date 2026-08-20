package spec

import (
	"path/filepath"
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

// Go version doesn't really need the sources, relying on on the sqlite db created by Python version

// InitDatabaseDir sets the database directory relative to the given base path
func InitDatabaseDir(basePath string) {
	DatabaseDir = filepath.Join(basePath, DataBaseDirName)
}
