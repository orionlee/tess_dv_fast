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
	TCESRadiusProvIsSolar bool
	TCEDitcoMsky    float64
	TCEDitcoMskyErr float64
	TCEDiccoMsky    float64
	TCEDiccoMskyErr float64
}

// SpocTCEDisplayInfo represents formatted TCE info for display
type SpocTCEDisplayInfo struct {
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
	DepthPercent        float64
	PlanetRadius string  // HTML-formatted string, to highlight entries of which the radius is not reliable
	ImpactB      float64
	SectorSpan   int
}

type TessSpocTCEDisplayInfo struct {
	ID           string
	DVS          string
	DVM          string
	DVR          string
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

	rows, err := db.Query("SELECT ticid, exomast_id, sectors, tce_plnt_num, dvs, dvm, dvr, tce_depth, tce_period, tce_time0bt, tce_duration, tce_prad, tce_impact, tce_sradius_prov_is_solar, tce_ditco_msky, tce_ditco_msky_err, tce_dicco_msky, tce_dicco_msky_err FROM tess_tcestats WHERE ticid = ?", tic)
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
			&r.TCESRadiusProvIsSolar,
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

	// Sort results the same way as Python version:
	// 1. by ticid (ascending)
	// 2. by sectors_span (descending - multi-sector first)
	// 3. by exomast_id (ascending)
	sortTCERecords(records)

	return records, nil
}

// GetTessSpocTCEInfosOfTIC retrieves TESS-SPOC TCE information for a given TIC ID
// TESS-SPOC (FFI) does not have tcedepth, tceperiod, tce_time0bt, tce_duration, etc.
// So we return records with minimal metadata
func GetTessSpocTCEInfosOfTIC(tic int64) ([]TCERecord, error) {
	dbPath := spec.DatabaseDir + "/" + spec.TessSpocDBName
	// Use proper URI format for modernc.org/sqlite with encoded path
	dsn := "file:" + url.QueryEscape(dbPath) + "?mode=ro"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to open database %s: %w", dbPath, err)
	}
	defer db.Close()

	// TESS-SPOC table has: ticid, sectors, tce_plnt_num, and that's mostly it
	// No TCE parameters like depth, period, etc.
	rows, err := db.Query("SELECT ticid, sectors, tce_plnt_num FROM tess_spoc_tcestats WHERE ticid = ?", tic)
	if err != nil {
		return nil, fmt.Errorf("failed to query database: %w", err)
	}
	defer rows.Close()

	var records []TCERecord
	for rows.Next() {
		var r TCERecord
		if err := rows.Scan(
			&r.TICID,
			&r.Sectors,
			&r.TCEPlanetNum,
		); err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}
		// Generate IDs and product filenames for TESS-SPOC
		r.ExoMastID = generateTessSpocID(r)
		r.DVS = generateTessSpocDVS(r)
		r.DVM = generateTessSpocDVM(r)
		r.DVR = generateTessSpocDVR(r)
		records = append(records, r)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	// Sort results the same way as Python version:
	// 1. by ticid (ascending)
	// 2. by sectors_span (descending - multi-sector first)
	// 3. by exomast_id (ascending)
	sortTCERecords(records)

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

// generateTessSpocID creates a unique ID for TESS-SPOC TCEs
// Format: TIC<ticid>S<start_sector>S<end_sector>TCE<plnt_num>_f
//         essentially exomast_id with a "_f" suffix (to signify it is from TESS-SPOC)
func generateTessSpocID(r TCERecord) string {
	return fmt.Sprintf("TIC%d%s", r.TICID, strings.ToUpper(strings.ReplaceAll(r.Sectors, "-", ""))) + fmt.Sprintf("TCE%d", r.TCEPlanetNum) + "_f"
}

// generateTessSpocDVS generates the DVS filename for TESS-SPOC
func generateTessSpocDVS(r TCERecord) string {
	ticid := fmt.Sprintf("%016d", r.TICID)
	plntNum := fmt.Sprintf("%02d", r.TCEPlanetNum)
	return fmt.Sprintf("hlsp_tess-spoc_tess_phot_%s-%s_tess_v1_dvs-%s.pdf", ticid, r.Sectors, plntNum)
}

// generateTessSpocDVM generates the DVM filename for TESS-SPOC
func generateTessSpocDVM(r TCERecord) string {
	ticid := fmt.Sprintf("%016d", r.TICID)
	return fmt.Sprintf("hlsp_tess-spoc_tess_phot_%s-%s_tess_v1_dvm.pdf", ticid, r.Sectors)
}

// generateTessSpocDVR generates the DVR filename for TESS-SPOC
func generateTessSpocDVR(r TCERecord) string {
	ticid := fmt.Sprintf("%016d", r.TICID)
	return fmt.Sprintf("hlsp_tess-spoc_tess_phot_%s-%s_tess_v1_dvr.pdf", ticid, r.Sectors)
}

// sortTCERecords sorts TCE records in the same way as the Python version:
// 1. by TICID (ascending)
// 2. by SectorSpan (descending - multi-sector TCEs come first)
// 3. by ExoMastID (ascending)
func sortTCERecords(records []TCERecord) {
	// Pre-calculate sector spans for sorting
	spans := make([]int, len(records))
	for i, r := range records {
		spans[i] = GetSectorsSpan(r.Sectors)
	}

	// Sort using Go's built-in sort
	for i := 0; i < len(records)-1; i++ {
		for j := 0; j < len(records)-i-1; j++ {
			// Compare TICID first (ascending)
			if records[j].TICID != records[j+1].TICID {
				if records[j].TICID > records[j+1].TICID {
					records[j], records[j+1] = records[j+1], records[j]
					spans[j], spans[j+1] = spans[j+1], spans[j]
				}
				continue
			}

			// Same TICID: compare SectorSpan (descending - larger first)
			if spans[j] != spans[j+1] {
				if spans[j] < spans[j+1] {
					records[j], records[j+1] = records[j+1], records[j]
					spans[j], spans[j+1] = spans[j+1], spans[j]
				}
				continue
			}

			// Same TICID and SectorSpan: compare ExoMastID (ascending)
			if strings.ToLower(records[j].ExoMastID) > strings.ToLower(records[j+1].ExoMastID) {
				records[j], records[j+1] = records[j+1], records[j]
				spans[j], spans[j+1] = spans[j+1], spans[j]
			}
		}
	}
}

// ToSpocProductURL converts product filenames to MAST server URL
func ToSpocProductURL(filename string) string {
	return fmt.Sprintf("https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:TESS/product/%s", filename)
}

// ToTessSpocProductURL converts TESS-SPOC product filenames to MAST server URL
// e.g., hlsp_tess-spoc_tess_phot_0000000033979459-s0056-s0069_tess_v1_dvs-01.pdf
//
//	hlsp_tess-spoc_tess_phot_0000000033979459-s0056-s0069_tess_v1_dvm.pdf
func ToTessSpocProductURL(filename string) string {
	re := regexp.MustCompile(`hlsp_tess-spoc_tess_phot_0+?([1-9]\d+)-(s\d{4}-s\d{4})`)
	matches := re.FindStringSubmatch(filename)
	if len(matches) < 3 {
		return ""
	}

	ticid := matches[1]
	sectors := matches[2]

	// Split sector_start and sector_end
	sectorParts := strings.Split(sectors, "-")
	sectorStart := sectorParts[0]
	sectorEnd := sectorParts[1]

	// Use single sector if both are the same
	if sectorStart == sectorEnd {
		sectors = sectorStart
	}

	// Pad ticid to 16 digits
	ticidPadded := fmt.Sprintf("%016s", ticid)

	// Split the ticid into 4 parts for the subdirectory pattern
	t1 := ticidPadded[0:4]
	t2 := ticidPadded[4:8]
	t3 := ticidPadded[8:12]
	t4 := ticidPadded[12:16]

	return fmt.Sprintf("https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:HLSP/tess-spoc/%s/target/%s/%s/%s/%s/%s", sectors, t1, t2, t3, t4, filename)
}

func formatPlanetRadius(pRadius float64, isSRadiusSolar bool) string {
	style := ""
	if isSRadiusSolar {
		style = ` style="color: red; font-weight: bold;"`
	}
	return fmt.Sprintf("<span%s>%.3f</span>", style, pRadius)
}

// FormatSpocTCEForDisplay converts a SPOC TCE record to display format with HTML formatting
func FormatSpocTCEForDisplay(record TCERecord) SpocTCEDisplayInfo {
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
	dvsLink := formatSpocProductLink(record.DVS)
	dvmLink := formatSpocProductLink(record.DVM)
	dvrLink := formatSpocProductLink(record.DVR)

	return SpocTCEDisplayInfo{
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
		DepthPercent:        depthPct,
		PlanetRadius: formatPlanetRadius(pRadiusJupiter, record.TCESRadiusProvIsSolar),
		ImpactB:      record.TCEImpact,
		SectorSpan:   GetSectorsSpan(record.Sectors),
	}
}

// FormatTessSpocTCEForDisplay converts a SPOC TCE record to display format with HTML formatting
func FormatTessSpocTCEForDisplay(record TCERecord) TessSpocTCEDisplayInfo {
	// Format DVS, DVM, DVR as links to MAST products
		dvsLink := formatTessSpocProductLink(record.DVS)
	dvmLink := formatTessSpocProductLink(record.DVM)
	dvrLink := formatTessSpocProductLink(record.DVR)

	re := regexp.MustCompile(`TIC\d+`)
	idAbbrev := strings.ToLower(re.ReplaceAllString(
		record.ExoMastID, // TODO: rename record.ExoMastID.  or have a separate TessSpocTCERecord
		""))

	return TessSpocTCEDisplayInfo{
		ID:          idAbbrev,
		DVS:          dvsLink,
		DVM:          dvmLink,
		DVR:          dvrLink,
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

// formatSpocProductLink formats a product filename as a clickable link to MAST
func formatSpocProductLink(filename string) string {
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
	return fmt.Sprintf(`<a target="_blank" href="%s">%s</a>`, ToSpocProductURL(filename), linkText)
}


// formatProductLink formats a product filename as a clickable link to MAST
func formatTessSpocProductLink(filename string) string {
	if filename == "" {
		return ""
	}
	// Extract the product type (dvs, dvm, or dvr) from filename
	// e.g., "tess...._dvs-01.pdf" -> "dvs", "tess...._dvm.pdf" -> "dvm"
	linkText := filename
	if idx := strings.LastIndex(filename, "_"); idx != -1 {
		// Get the part after the last underscore and before the extension
		suffix := filename[idx+1:]
		if idx2 := strings.Index(suffix, "."); idx2 != -1 {
			linkText = suffix[:idx2]
		}
		// to furhter map "dvs-01" to "dvs"
		if idx3 := strings.Index(linkText, "-"); idx3 != -1 {
			linkText = linkText[:idx3]
		}
	}
	return fmt.Sprintf(`<a target="_blank" href="%s">%s</a>`, ToTessSpocProductURL(filename), linkText)
}

// formatCodesAsInput wraps the codes string in an HTML input element for easy copying
func formatCodesAsInput(codes string) string {
	return fmt.Sprintf(`<input type="text" value='%s' readonly style="margin-left: 3ch; font-size: 90%%; color: #666; width: 10ch;" onclick="this.select();">`, codes)
}

// RenderSpocTCETable renders TCE records as an HTML table
func RenderSpocTCETable(records []TCERecord) string {
	if len(records) == 0 {
		return "No SPOC TCE"
	}

	var html strings.Builder
	html.WriteString(`<table id="table_spoc"><thead><tr>`)
	// CSS classes col0, col1, etc. are used for
	// in-table search/filtering at client side using list.js
	html.WriteString(`<th class="col_heading level0 col0">exomast_id</th>`)
	html.WriteString(`<th class="col_heading level0 col1">dvs</th>`)
	html.WriteString(`<th class="col_heading level0 col2">dvm</th>`)
	html.WriteString(`<th class="col_heading level0 col3">dvr</th>`)
	html.WriteString(`<th class="col_heading level0 col4">Rp</th>`)
	html.WriteString(`<th class="col_heading level0 col5">Epoch</th>`)
	html.WriteString(`<th class="col_heading level0 col6">Duration</th>`)
	html.WriteString(`<th class="col_heading level0 col7">Period</th>`)
	html.WriteString(`<th class="col_heading level0 col8">Depth</th>`)
	html.WriteString(`<th class="col_heading level0 col9">Impact b</th>`)
	html.WriteString(`<th class="col_heading level0 col10">TicOffset</th>`)
	html.WriteString(`<th class="col_heading level0 col11">OotOffset</th>`)
	html.WriteString(`<th class="col_heading level0 col12">Codes</th>`)
	html.WriteString(`</tr></thead><tbody>`)

	for _, record := range records {
		display := FormatSpocTCEForDisplay(record)
		html.WriteString(`<tr>`)
		html.WriteString(fmt.Sprintf(`<td class="col0">%s</td>`, display.ExoMastID))
		html.WriteString(fmt.Sprintf(`<td class="col1">%s</td>`, display.DVS))
		html.WriteString(fmt.Sprintf(`<td class="col2">%s</td>`, display.DVM))
		html.WriteString(fmt.Sprintf(`<td class="col3">%s</td>`, display.DVR))
		html.WriteString(fmt.Sprintf(`<td class="col4">%s</td>`, display.PlanetRadius))
		html.WriteString(fmt.Sprintf(`<td class="col5">%.2f</td>`, display.Epoch))
		html.WriteString(fmt.Sprintf(`<td class="col6">%.4f</td>`, display.Duration))
		html.WriteString(fmt.Sprintf(`<td class="col7">%.6f</td>`, display.Period))
		html.WriteString(fmt.Sprintf(`<td class="col8">%.4f</td>`, display.DepthPercent))
		html.WriteString(fmt.Sprintf(`<td class="col9">%.2f</td>`, display.ImpactB))
		html.WriteString(fmt.Sprintf(`<td class="col10">%s</td>`, display.TICOffset))
		html.WriteString(fmt.Sprintf(`<td class="col11">%s</td>`, display.OotOffset))
		html.WriteString(fmt.Sprintf(`<td class="col12">%s</td>`, display.Codes))
		html.WriteString(`</tr>`)
	}

	html.WriteString(`</tbody></table>`)
	return common.AddHTMLColumnUnits(html.String())
}

// RenderTessSpocTCETable renders TESS-SPOC TCE records as an HTML table with minimal columns
func RenderTessSpocTCETable(records []TCERecord) string {
	if len(records) == 0 {
		return "No TESS-SPOC TCE"
	}

	var html strings.Builder
	html.WriteString(`<table id="table_tess_spoc"><thead><tr>`)
	// CSS classes col0, col1, etc. are used for
	// in-table search/filtering at client side using list.js
	html.WriteString(`<th class="col_heading level0 col0">id</th>`)
	html.WriteString(`<th class="col_heading level0 col1">dvs</th>`)
	html.WriteString(`<th class="col_heading level0 col2">dvm</th>`)
	html.WriteString(`<th class="col_heading level0 col3">dvr</th>`)
	html.WriteString(`</tr></thead><tbody>`)

	for _, record := range records {
		display := FormatTessSpocTCEForDisplay(record)
		html.WriteString(`<tr>`)
		html.WriteString(fmt.Sprintf(`<td class="col0">%s</td>`, display.ID))
		html.WriteString(fmt.Sprintf(`<td class="col1">%s</td>`, display.DVS))
		html.WriteString(fmt.Sprintf(`<td class="col2">%s</td>`, display.DVM))
		html.WriteString(fmt.Sprintf(`<td class="col3">%s</td>`, display.DVR))
		html.WriteString(`</tr>`)
	}

	html.WriteString(`</tbody></table>`)
	return html.String()
}
