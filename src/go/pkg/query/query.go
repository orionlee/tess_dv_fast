package query

import (
	"database/sql"
	"fmt"
	"net/url"
	"regexp"
	"strconv"
	"strings"

	"github.com/orionlee/tess_dv_fast/pkg/common"
	"github.com/orionlee/tess_dv_fast/pkg/spec"
	_ "modernc.org/sqlite"
)

// TCERecord represents a single TCE record from the database
type TCERecord struct {
	TICID           int64
	ExoMastID       string
	Sectors         string
	TCEPlanetNum    int
	DVS             string
	DVM             string
	DVR             string
	TCEDepth        float64
	TCEPeriod       float64
	TCETime0BT      float64
	TCEDuration     float64
	TCEPRad         float64
	TCEImpact       float64
	TCEDitcoMsky    float64
	TCEDitcoMskyErr float64
	TCEDiccoMsky    float64
	TCEDiccoMskyErr float64
}

// TCEDisplayInfo represents formatted TCE info for display
type TCEDisplayInfo struct {
	ExoMastID    string
	DVS          string
	DVM          string
	DVR          string
	TICOffset    string
	OotOffset    string
	Codes        string
	Period       float64
	Epoch        float64
	Duration     float64
	Depth        float64
	PlanetRadius float64
	ImpactB      float64
	SectorSpan   int
}

// GetTCEInfosOfTIC retrieves TCE information for a given TIC ID
func GetTCEInfosOfTIC(tic int64) ([]TCERecord, error) {
	dbPath := spec.DatabaseDir + "/" + spec.TCEStatsDBName
	// Use proper URI format for modernc.org/sqlite with encoded path
	dsn := "file:" + url.QueryEscape(dbPath) + "?mode=ro"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to open database %s: %w", dbPath, err)
	}
	defer db.Close()

	rows, err := db.Query("SELECT ticid, exomast_id, sectors, tce_plnt_num, dvs, dvm, dvr, tce_depth, tce_period, tce_time0bt, tce_duration, tce_prad, tce_impact, tce_ditco_msky, tce_ditco_msky_err, tce_dicco_msky, tce_dicco_msky_err FROM tess_tcestats WHERE ticid = ?", tic)
	if err != nil {
		return nil, fmt.Errorf("failed to query database: %w", err)
	}
	defer rows.Close()

	var records []TCERecord
	for rows.Next() {
		var r TCERecord
		if err := rows.Scan(
			&r.TICID,
			&r.ExoMastID,
			&r.Sectors,
			&r.TCEPlanetNum,
			&r.DVS,
			&r.DVM,
			&r.DVR,
			&r.TCEDepth,
			&r.TCEPeriod,
			&r.TCETime0BT,
			&r.TCEDuration,
			&r.TCEPRad,
			&r.TCEImpact,
			&r.TCEDitcoMsky,
			&r.TCEDitcoMskyErr,
			&r.TCEDiccoMsky,
			&r.TCEDiccoMskyErr,
		); err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}
		records = append(records, r)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	return records, nil
}

// GetSectorsSpan calculates the span of sectors for a multi-sector TCE
func GetSectorsSpan(sectorsStr string) int {
	re := regexp.MustCompile(`s(\d+)-s(\d+)`)
	matches := re.FindStringSubmatch(sectorsStr)
	if len(matches) < 3 {
		return -1
	}

	start, _ := strconv.Atoi(matches[1])
	end, _ := strconv.Atoi(matches[2])
	return end - start + 1
}

// ToProductURL converts product filenames to MAST server URL
func ToProductURL(filename string) string {
	return fmt.Sprintf("https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:TESS/product/%s", filename)
}

// FormatTCEForDisplay converts a TCE record to display format with HTML formatting
func FormatTCEForDisplay(record TCERecord) TCEDisplayInfo {
	pRadiusJupiter := record.TCEPRad * common.REarthToRJupiter
	depthPct := record.TCEDepth / 10000.0
	ditcoSig := 0.0
	if record.TCEDitcoMskyErr != 0 {
		ditcoSig = record.TCEDitcoMsky / record.TCEDitcoMskyErr
	}
	diccoSig := 0.0
	if record.TCEDiccoMskyErr != 0 {
		diccoSig = record.TCEDiccoMsky / record.TCEDiccoMskyErr
	}

	// Format DVS, DVM, DVR as links to MAST products
	dvsLink := formatProductLink(record.DVS)
	dvmLink := formatProductLink(record.DVM)
	dvrLink := formatProductLink(record.DVR)

	return TCEDisplayInfo{
		ExoMastID:    common.FormatExoMastID(record.ExoMastID),
		DVS:          dvsLink,
		DVM:          dvmLink,
		DVR:          dvrLink,
		TICOffset:    common.FormatOffsetNSigma(fmt.Sprintf("%.1f|%.1f", record.TCEDitcoMsky, ditcoSig)),
		OotOffset:    common.FormatOffsetNSigma(fmt.Sprintf("%.1f|%.1f", record.TCEDiccoMsky, diccoSig)),
		Codes:        formatCodesAsInput(generateCodes(record)),
		Period:       record.TCEPeriod,
		Epoch:        record.TCETime0BT,
		Duration:     record.TCEDuration,
		Depth:        depthPct,
		PlanetRadius: pRadiusJupiter,
		ImpactB:      record.TCEImpact,
		SectorSpan:   GetSectorsSpan(record.Sectors),
	}
}

// generateCodes creates the observing codes string
func generateCodes(record TCERecord) string {
	exoIDShort := strings.ToLower(regexp.MustCompile(`TIC\d+`).ReplaceAllString(record.ExoMastID, ""))
	return fmt.Sprintf(
		"epoch=%v, duration_hr=%v, period=%v, label=\"%s\", transit_depth_percent=%.4f,",
		record.TCETime0BT,
		record.TCEDuration,
		record.TCEPeriod,
		exoIDShort,
		record.TCEDepth/10000.0,
	)
}

// formatProductLink formats a product filename as a clickable link to MAST
func formatProductLink(filename string) string {
	if filename == "" {
		return ""
	}
	// Extract the product type (dvs, dvm, or dvr) from filename
	// e.g., "tess...._dvs.pdf" -> "dvs"
	linkText := filename
	if idx := strings.LastIndex(filename, "_"); idx != -1 {
		// Get the part after the last underscore and before the extension
		suffix := filename[idx+1:]
		if idx2 := strings.Index(suffix, "."); idx2 != -1 {
			linkText = suffix[:idx2]
		}
	}
	return fmt.Sprintf(`<a target="_blank" href="%s">%s</a>`, ToProductURL(filename), linkText)
}

// formatCodesAsInput wraps the codes string in an HTML input element for easy copying
func formatCodesAsInput(codes string) string {
	return fmt.Sprintf(`<input type="text" value='%s' readonly style="margin-left: 3ch; font-size: 90%%; color: #666; width: 10ch;" onclick="this.select();">`, codes)
}

// RenderTCETable renders TCE records as an HTML table
func RenderTCETable(records []TCERecord) string {
	if len(records) == 0 {
		return "No SPOC TCE"
	}

	var html strings.Builder
	html.WriteString(`<table id="table_spoc"><thead><tr>`)
	html.WriteString(`<th>exomast_id</th><th>dvs</th><th>dvm</th><th>dvr</th><th>Period</th><th>Epoch</th><th>Duration</th><th>Rp</th>`)
	html.WriteString(`<th>Depth</th><th>Impact b</th><th>TicOffset</th><th>OotOffset</th><th>Codes</th>`)
	html.WriteString(`</tr></thead><tbody>`)

	for _, record := range records {
		display := FormatTCEForDisplay(record)
		html.WriteString(`<tr>`)
		html.WriteString(fmt.Sprintf(`<td>%s</td>`, display.ExoMastID))
		html.WriteString(fmt.Sprintf(`<td>%s</td>`, display.DVS))
		html.WriteString(fmt.Sprintf(`<td>%s</td>`, display.DVM))
		html.WriteString(fmt.Sprintf(`<td>%s</td>`, display.DVR))
		html.WriteString(fmt.Sprintf(`<td>%.6f</td>`, display.Period))
		html.WriteString(fmt.Sprintf(`<td>%.1f</td>`, display.Epoch))
		html.WriteString(fmt.Sprintf(`<td>%.3f</td>`, display.Duration))
		html.WriteString(fmt.Sprintf(`<td>%.4f</td>`, display.PlanetRadius))
		html.WriteString(fmt.Sprintf(`<td>%.4f</td>`, display.Depth*100))
		html.WriteString(fmt.Sprintf(`<td>%.3f</td>`, display.ImpactB))
		html.WriteString(fmt.Sprintf(`<td>%s</td>`, display.TICOffset))
		html.WriteString(fmt.Sprintf(`<td>%s</td>`, display.OotOffset))
		html.WriteString(fmt.Sprintf(`<td>%s</td>`, display.Codes))
		html.WriteString(`</tr>`)
	}

	html.WriteString(`</tbody></table>`)
	return common.AddHTMLColumnUnits(html.String())
}
