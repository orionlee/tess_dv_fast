package main

import (
	"fmt"
	"html"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/orionlee/tess_dv_fast/pkg/query"
	"github.com/orionlee/tess_dv_fast/pkg/spec"
)

const (
	exoFOPBaseURL = "https://exofop.ipac.caltech.edu/tess/target.php"
	buildDate     = "unknown"
	buildCommit   = "unknown"
	defaultPort   = "8080"
)

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

	// Query SPOC TCEs
	spocRecords, err := query.GetTCEInfosOfTIC(ticInt)
	if err != nil {
		log.Printf("Query failed for TIC %d: %v", ticInt, err)
		renderError(w, fmt.Sprintf("Database query failed. Please try again later. (Details: %s)", html.EscapeString(err.Error())), http.StatusInternalServerError)
		return
	}

	// Render content
	spocContent := query.RenderTCETable(spocRecords)
	spocContent = applyTableStyling(spocContent, "table_spoc", []int{0, 4, 5, 6, 7, 8, 9, 10, 11})

	// Generate response HTML
	ticEscaped := html.EscapeString(ticStr)
	totalTCEs := len(spocRecords)

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
                const options = {valueNames: ['col0', 'col4', 'col5', 'col6', 'col7', 'col8', 'col9', 'col10', 'col11']};
                const tceList = new List('result', options);
            }
        </script>
    </body>
</html>`,
		totalTCEs,
		ticEscaped,
		getStyleCSS(),
		exoFOPBaseURL,
		ticEscaped,
		ticEscaped,
		spocContent,
	)

	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, htmlContent)
	log.Printf("Query for TIC %d: found %d SPOC TCEs", ticInt, len(spocRecords))
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
            TIC: <input name="tic" type="number" placeholder="TIC id, e.g., 261136679"></input>
            <input type="Submit"></input>
        </form>
        <footer style="margin-top: 5vh; font-size: 85%%;">
            <p>SPOC (2 min cadence): based on data published by <a href="https://archive.stsci.edu/" target="_blank">MAST</a>:</p>
            <ul>
                <li><a href="https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_tce.html" target="_blank">TCE statistics bulk downloads</a> (<code>csv</code> files)</li>
                <li><a href="https://archive.stsci.edu/tess/bulk_downloads/bulk_downloads_ffi-tp-lc-dv.html" target="_blank">TESS DV files bulk downloads</a> (<code>sh</code> files)</li>
            </ul>
            Latest:
            <ul>
                <li>Single sector: %s</li>
                <li>Multi sector: %s</li>
            </ul>
            <br>
            <a href="https://github.com/orionlee/tess_dv_fast/" target="_blank">Sources / Issues</a><br>
        </footer>
    </body>
</html>`,
		spocWatermarks.SingleSector,
		spocWatermarks.MultiSector,
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
</style>`
}

func applyTableStyling(content string, tableID string, sortableCols []int) string {
	// Apply table ID
	re := regexp.MustCompile(`<table id="[^"]+"`)
	content = re.ReplaceAllString(content, fmt.Sprintf(`<table id="%s"`, tableID))

	// Apply sortable styling
	if len(sortableCols) > 0 {
		content = strings.Replace(content, "<tbody", `<tbody class="list"`, 1)
		for _, i := range sortableCols {
			oldClass := fmt.Sprintf(`class="col_heading level0 col%d"`, i)
			newClass := fmt.Sprintf(`class="col_heading level0 col%d sort" data-sort="col%d"`, i, i)
			content = strings.Replace(content, oldClass, newClass, 1)
		}
	}

	return content
}
