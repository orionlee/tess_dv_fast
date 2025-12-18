package main

import (
	"bufio"
	"fmt"
	"html"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"

	"github.com/orionlee/tess_dv_fast/pkg/query"
	"github.com/orionlee/tess_dv_fast/pkg/spec"
)

const (
	exoFOPBaseURL = "https://exofop.ipac.caltech.edu/tess/target.php"
	defaultPort   = "8080"
	spoc_table_id = "table_spoc"
)

// Sortable columns: col0 (exomast_id), col4-col11 (numeric columns), but NOT col1-col3 (product links) or col12 (codes)
//   - note: needs to be in sync with the javascript codes (List object) created
//     in handleTCES()
var spoc_sortable_columns_idx = []int{0, 4, 5, 6, 7, 8, 9, 10, 11}

// BEGIN read build commit SHA
var (
	// Cached SHA
	// This variable holds the string value after it is loaded.
	cachedSHA = ""

	// once ensures that the loadFirstLine function is executed only once.
	once sync.Once
)

func loadSHAFromFile() {
	// The code inside this function is intended to run once only.
	// store the SHA in the global cachedSHA

	exePath, err := os.Executable()
	if err != nil {
		log.Printf("Failed to locate build.txt for build SHA. err: %v", err)
		return
	}
	exeBaseDir := filepath.Dir(exePath)
	shaFilePath := exeBaseDir + "/" + "build.txt"
	file, err := os.Open(shaFilePath)
	if err != nil {
		log.Printf("Failed to open file: %s, err: %v", shaFilePath, err)
		// Handle the error as appropriate for your application.
		// Since we cannot return an error from an init function, we log it.
		return
	}
	defer file.Close() // Ensure the file is closed after reading.

	scanner := bufio.NewScanner(file)
	if scanner.Scan() { // Read the first line.
		cachedSHA = scanner.Text() // Get the line as a string.
	}

	if err := scanner.Err(); err != nil {
		log.Printf("Error during file scanning: %v", err)
	}
}

// getBuildSHA provides the cached first line of the file.
func getBuildSHA() string {
	// Call Do with the function to execute.
	// The function passed to Do takes no arguments.
	// We use a closure to pass filePath to loadFirstLine.
	once.Do(func() {
		loadSHAFromFile()
	})

	return cachedSHA
}

func getBuildSHAShort() string {
	sha := getBuildSHA()

	// Convert the string to a slice of runes (for getting a subset)
	runes := []rune(sha)

	if 8 >= len(runes) {
		return sha
	}
	return string(runes[:8])
}

// END read build commit SHA

func init() {
	// Initialize database directory from environment variable or executable location
	dbBasePath := os.Getenv("TESS_DB_BASE_PATH")
	if dbBasePath == "" {
		// If not set, use executable location
		exePath, err := os.Executable()
		if err == nil {
			// Get the directory containing the executable
			exeDir := filepath.Dir(exePath)
			dbBasePath = exeDir
		} else {
			// Fallback to current working directory
			dbBasePath = "."
		}
	}
	spec.InitDatabaseDir(dbBasePath)
}

func main() {
	http.HandleFunc("/", handleRoot)
	http.HandleFunc("/tces", handleTCES)

	// Get port from environment variable or use default
	port := os.Getenv("PORT")
	if port == "" {
		port = defaultPort
	}
	addr := ":" + port

	log.Printf("Server starting on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func handleRoot(w http.ResponseWriter, r *http.Request) {
	http.Redirect(w, r, "/tces", http.StatusMovedPermanently)
}

func handleTCES(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	ticStr := r.URL.Query().Get("tic")
	pipeline := r.URL.Query().Get("pipeline")
	// Return search form if no TIC provided
	if ticStr == "" {
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, renderHome())
		return
	}

	// Validate and parse TIC
	ticStr = strings.TrimSpace(ticStr)
	if ticStr == "" {
		renderError(w, "TIC cannot be empty.", http.StatusBadRequest)
		return
	}

	// Ensure TIC is a positive integer
	if !regexp.MustCompile(`^\d+$`).MatchString(ticStr) {
		renderError(w, fmt.Sprintf("Invalid TIC: %s. Must be a positive integer.", html.EscapeString(ticStr)), http.StatusBadRequest)
		return
	}

	ticInt, err := strconv.ParseInt(ticStr, 10, 64)
	if err != nil || ticInt <= 0 {
		renderError(w, fmt.Sprintf("Invalid TIC: %s. Must be a positive integer.", html.EscapeString(ticStr)), http.StatusBadRequest)
		return
	}

	// Query appropriate TCE database based on type
	var spocRecords []query.TCERecord
	var tessSpocRecords []query.TCERecord
	var showBoth bool

	switch pipeline {
	case "tess_spoc":
		// TESS-SPOC (FFI) TCEs only
		tessSpocRecords, err = query.GetTessSpocTCEInfosOfTIC(ticInt)
	case "spoc":
		// SPOC (2-min cadence) TCEs only
		spocRecords, err = query.GetTCEInfosOfTIC(ticInt)
	default:
		// Fetch both SPOC and TESS-SPOC by default
		showBoth = true
		spocRecords, err = query.GetTCEInfosOfTIC(ticInt)
		if err != nil {
			// Log but continue to try TESS-SPOC
			log.Printf("SPOC query failed for TIC %d: %v", ticInt, err)
		}
		tessSpocRecords, err = query.GetTessSpocTCEInfosOfTIC(ticInt)
		if err != nil {
			// Log but continue - may only have SPOC data
			log.Printf("TESS-SPOC query failed for TIC %d: %v", ticInt, err)
		}
	}

	// Render content
	var spocContent string
	var tessSpocContent string

	spocContent = query.RenderTCETable(spocRecords)
	spocContent = applyTableStyling(spocContent, "table_spoc", spoc_sortable_columns_idx)

	if len(tessSpocRecords) > 0 {
		tessSpocContent = query.RenderTessSpocTCETable(tessSpocRecords)
		// TESS-SPOC table doesn't need sorting styling since it only has 4 columns (id, dvs, dvm, dvr)
		// and id/dvs/dvm/dvr are not typically sortable
	}

	// Generate response HTML
	ticEscaped := html.EscapeString(ticStr)
	totalSpocTCEs := len(spocRecords)
	totalTessSpocTCEs := len(tessSpocRecords)

	// Build table HTML sections
	var tablesSectionHTML string
	if showBoth {
		// Show both SPOC and TESS-SPOC results
		tablesSectionHTML += fmt.Sprintf("<h2>SPOC (2-min cadence) - %d TCEs</h2>\n%s\n", totalSpocTCEs, spocContent)
		if totalTessSpocTCEs > 0 {
			tablesSectionHTML += fmt.Sprintf("<h2>TESS-SPOC (FFI) - %d TCEs</h2>\n<div id=\"tessSpocDupCtr\">\n  <span id=\"tessSpocDupMsg\"></span>\n  <button id=\"hideShowInSpocCtl\" onclick=\"document.body.classList.toggle('show_in_spoc');\"></button>\n</div>\n%s\n", totalTessSpocTCEs, tessSpocContent)
		}
	} else if pipeline == "spoc" {
		// SPOC only
		tablesSectionHTML = spocContent
	} else {
		// TESS-SPOC only
		tablesSectionHTML = tessSpocContent
	}

	htmlContent := fmt.Sprintf(`<!DOCTYPE html>
<html>
	<head>
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<link rel="icon" href="data:,">
		<title>(%d) TCEs for TIC %s</title>
        %s
    </head>
    <body>
        <div id="result">
            <h1>TCEs for TIC <a href="%s?id=%s" target="_exofop">%s</a>
            <input class="search" placeholder="Search table" style="margin-left: 40ch;" accesskey="/">
            </h1>
            %s
        </div>

        <hr>
        <footer>
            <a href="/tces">New Search</a>
        </footer>

        <script src="https://cdn.jsdelivr.net/gh/javve/list.js@2.3.1/dist/list.min.js"></script>
        <script>
            if (document.querySelector('#result table')) {
			    // valueNames should be in sync with spoc_sortable_columns at sever side
                const options = {valueNames: ['col0', 'col4', 'col5', 'col6', 'col7', 'col8', 'col9', 'col10', 'col11']};
                const tceList = new List('result', options);
            }

            // Hide/show TESS-SPOC duplicates of SPOC results
            function addHideShowForTessSpocDupRows() {
                // mark rows (that are "duplicates" of SPOC TCEs) with css class
                const spocTceIds = Array.from(document.querySelectorAll('table#table_spoc tbody td:nth-of-type(1)')).map(td => td.textContent);
                let numInSpoc = 0;
                document.querySelectorAll('table#table_tess_spoc tbody tr').forEach(tr => {
                    // TESS-SPOC id generation: SPOC id with '_f' suffix. strip the suffix for comparison
                    const curId = tr.querySelector('td:nth-of-type(1)').textContent.replace('_f', '').replace('_ftce', '_tce');
                    if (spocTceIds.includes(curId)) {
                        tr.classList.add('in_spoc');
                        numInSpoc++;
                    }
                });
                if (numInSpoc > 0) {
                    document.getElementById('tessSpocDupMsg').textContent = numInSpoc + ' TCEs have SPOC counterparts.';
                } else {
                    document.getElementById('tessSpocDupCtr').style.display = 'none';
                }
            }

            if (document.querySelector('#table_tess_spoc')) {
                addHideShowForTessSpocDupRows();
            }
        </script>
    </body>
</html>`,
		totalSpocTCEs + totalTessSpocTCEs,
		ticEscaped,
		getStyleCSS(),
		exoFOPBaseURL,
		ticEscaped,
		ticEscaped,
		tablesSectionHTML,
	)

	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, htmlContent)
	if showBoth {
		log.Printf("Query for TIC %d: found %d SPOC TCEs, %d TESS-SPOC TCEs", ticInt, totalSpocTCEs, totalTessSpocTCEs)
	} else if pipeline == "spoc" {
		log.Printf("Query for TIC %d (SPOC): found %d TCEs", ticInt, totalSpocTCEs)
	} else {
		log.Printf("Query for TIC %d (TESS-SPOC): found %d TCEs", ticInt, totalTessSpocTCEs)
	}
}

func renderHome() string {
	// TODO: add build commit SHA and links
	spocWatermarks := spec.GetHighWatermarks()

	return fmt.Sprintf(`<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="data:,">
        <title>Search TESS TCEs</title>
    </head>
    <body>
        <h1>Search TESS TCEs</h1>
        <style type="text/css">
        body {
            margin-left: 16px;
            font-family: sans-serif;
        }
        </style>
        <form>
            <div>
                TIC: <input name="tic" type="number" placeholder="TIC id, e.g., 261136679"></input>
                <input type="Submit"></input>
            </div>
			<br>
<!-- Hide the optional pipeline form input for now.
            <div>
                Pipeline:
                <select name="pipeline">
                    <option value="">all</option>
                    <option value="spoc">SPOC</option>
                    <option value="tess_spoc">TESS-SPOC</option>
                </select>
            </div>
-->
        </form>
        <footer style="margin-top: 5vh; font-size: 85%%;">
            <p><strong>SPOC</strong> (2 min cadence): based on data published by <a href="https://archive.stsci.edu/" target="_blank">MAST</a>:</p>
            <ul>
                <li><a href="https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_tce.html" target="_blank">TCE statistics bulk downloads</a> (<code>csv</code> files)</li>
                <li><a href="https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_ffi-tp-lc-dv.html" target="_blank">TESS DV files bulk downloads</a> (<code>sh</code> files)</li>
            </ul>
            Latest SPOC:
            <ul>
                <li>Single sector: %s</li>
                <li>Multi sector: %s</li>
            </ul>

            <p><strong>TESS-SPOC</strong> (FFI): based on data published by <a href="https://archive.stsci.edu/hlsp/tess-spoc" target="_blank">MAST HLSP TESS-SPOC</a>:</p>
            Latest TESS-SPOC:
            <ul>
                <li>Single sector: %s</li>
                <li>Multi sector: %s</li>
            </ul>

            <br>
            <a href="https://github.com/orionlee/tess_dv_fast/" target="_blank">Sources / Issues</a><br>
            Build:
            <a target="_blank" href="https://github.com/orionlee/tess_dv_fast/commit/%s"
                >%s</a><br>
        </footer>
    </body>
</html>`,
		spocWatermarks.SpocSingleSector,
		spocWatermarks.SpocMultiSector,
		spocWatermarks.TessSpocSingleSector,
		spocWatermarks.TessSpocMultiSector,
		getBuildSHA(),
		getBuildSHAShort(),
	)
}

func renderError(w http.ResponseWriter, errorMsg string, statusCode int) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(statusCode)
	fmt.Fprintf(w, `<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="data:,">
        <title>Error - Search TESS TCEs</title>
        <style type="text/css">
            body {
                margin-left: 16px;
                font-family: sans-serif;
            }
            .error {
                color: #d32f2f;
                border: 1px solid #d32f2f;
                padding: 12px;
                border-radius: 4px;
                background-color: #ffebee;
            }
        </style>
    </head>
    <body>
        <h1>Search TESS TCEs</h1>
        <div class="error">
            <strong>Error:</strong> %s
        </div>
        <p><a href="/tces">Back to search</a></p>
    </body>
</html>`, html.EscapeString(errorMsg))
}

func getStyleCSS() string {
	return `<style type="text/css">
body {
    margin-left: 16px;
    font-family: sans-serif;
}

footer {
    margin-bottom: 16px;
}

h1 a {
    text-decoration: none;
}

table {
    border-collapse: collapse;
    border: none;
    font-size: 0.9rem;
}

thead th {
    position: sticky;
    top: 0;
    background-color: darkgray;
    color: white;
}

th, td {
    padding: 5px 10px;
}

tbody tr:nth-child(even) {
    background-color: #f5f5f5;
}

th.sort {
    cursor: pointer;
}

.sort.asc, .sort.desc {
    color: yellow;
}

.sort.asc::after {
    content: "\025B4";
    padding-left: 3px;
}

.sort.desc::after {
    content: "\025BE";
    padding-left: 3px;
}

/* for hide show TESS-SPOC "duplicates" of SPOC */
h2 {
    font-size: 1.2rem;
}

#tessSpocDupCtr {
    margin-bottom: 6px;
    margin-left: 12px;
    font-size: 80%;
}

tr.in_spoc {
    display: none;
}

.show_in_spoc tr.in_spoc {
    display: table-row;
}

#hideShowInSpocCtl {
    font-size: 80%;
}

#hideShowInSpocCtl::before {
    content: "Show";
}

.show_in_spoc #hideShowInSpocCtl::before {
    content: "Hide";
}
</style>`
}

func applyTableStyling(content string, tableID string, sortableCols []int) string {
	// Apply table ID
	re := regexp.MustCompile(`<table id="[^"]+"`)
	content = re.ReplaceAllString(content, fmt.Sprintf(`<table id="%s"`, tableID))

	if len(sortableCols) > 0 {
		// make table searchable / sortable by https://github.com/javve/list.js
		content = strings.Replace(content, "<tbody", `<tbody class="list"`, 1)

		// Create a map for quick lookup of sortable columns
		sortableMap := make(map[int]bool)
		for _, col := range sortableCols {
			sortableMap[col] = true
		}

		// Replace ALL header occurrences for sortable columns
		for col := 0; col <= 12; col++ {
			if sortableMap[col] {
				oldClass := fmt.Sprintf(`<th class="col_heading level0 col%d">`, col)
				newClass := fmt.Sprintf(`<th class="col_heading level0 col%d sort" data-sort="col%d">`, col, col)
				content = strings.ReplaceAll(content, oldClass, newClass)
			}
		}
	}

	return content
}
