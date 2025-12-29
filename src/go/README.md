# TESS DV Fast - Go Port

This is a Go language port of the Python `tess_dv_fast` web application for searching TESS TCE data validation reports.

## Project Structure

```
src/go/
├── main.go                    # Main web application (Gin-based HTTP server)
├── go.mod                     # Go module definition
├── pkg/
│   ├── common/                # Common utilities and formatters
│   │   └── common.go
│   ├── query/                 # TCE query and rendering logic
│   │   └── query.go
│   └── spec/                  # Data specifications and constants
│       └── spec.go
```

## Components

### `main.go`
- HTTP web server using standard library `net/http`
- Routes:
  - `GET /` - Redirects to `/tces`
  - `GET /tces` - Search and display TCE information
- Input validation and error handling
- HTML rendering and table formatting
- Environment variable support for PORT and database path

### `pkg/common/common.go`
- Physical constants (radius conversions)
- HTML formatting functions:
  - `FormatExoMastID()` - Format ExoMAST links
  - `FormatOffsetNSigma()` - Format offset values with significance coloring
  - `FormatCodes()` - Format TCE observation codes
  - `FormatProductURL()` - Format product download links
  - `AddHTMLColumnUnits()` - Add units to table headers

### `pkg/query/query.go`
- Database querying for TCE records
- SQLite3 connection and queries
- TCE data processing and formatting
- HTML table rendering

### `pkg/spec/spec.go`
- Data specifications and source URLs
- Configuration constants
- High water mark detection from source URLs

## Building

```bash
cd src/go
go mod download
go build -o tess_dv_fast_server main.go
```

## Running

```bash
./tess_dv_fast_server
```

Server will start on `http://localhost:8080`

### Environment Variables

The server supports optional environment variables to customize behavior:

- `PORT` - HTTP port to listen on (default: `8080`)
  ```bash
  PORT=9090 ./tess_dv_fast_server
  ```

- `TESS_DB_BASE_PATH` - Base directory for the database (default: executable directory)
  ```bash
  TESS_DB_BASE_PATH=/path/to/data ./tess_dv_fast_server
  ```

- Both can be used together:
  ```bash
  TESS_DB_BASE_PATH=/data PORT=9000 ./tess_dv_fast_server
  ```

## Testing

To test the application:

```bash
# Start the server with default settings
./tess_dv_fast_server

# Or with custom port
PORT=9000 ./tess_dv_fast_server

# Or with custom database path
TESS_DB_BASE_PATH=/path/to/data ./tess_dv_fast_server

# In another terminal, test the endpoints
curl 'http://localhost:8080/tces'              # Get search form
curl 'http://localhost:8080/tces?tic=261136679' # Search a TIC
```

## Deployment to Google Cloud Run

```bash
# copy the SQLite db files, so they can be included in the deployment
mkdir -p data/tess_dv_fast
cp ../../data/tess_dv_fast/*.db ./data/tess_dv_fast/
# include build commit SHA
echo `git rev-parse HEAD` > build.txt
gcloud run deploy <service-name> --source .
```

## Features

- TIC input validation (must be positive integer)
- SQLite database queries with proper error handling
- HTML table rendering with sorting capabilities
- XSS protection via HTML escaping
- Responsive web interface
- List.js integration for table search and sort functionality

## Dependencies

- `modernc.org/sqlite` - Pure Go SQLite3 driver (no CGO required)

## Database

Expects SQLite database at: `data/tess_dv_fast/tess_tcestats.db`

The database should contain a `tess_tcestats` table with columns:
- ticid (INTEGER)
- exomast_id (TEXT)
- sectors (TEXT)
- tce_plnt_num (INTEGER)
- tce_depth, tce_period, tce_time0bt, tce_duration (REAL)
- tce_prad, tce_impact (REAL)
- tce_ditco_msky, tce_ditco_msky_err (REAL)
- tce_dicco_msky, tce_dicco_msky_err (REAL)

## Differences from Python Version

1. **Database**: Go version queries SQLite directly (Python had CSV/DB options)
2. **Framework**: Uses standard library HTTP server for routing (Python used Flask)
3. **Performance**: Typically faster due to Go's compiled nature
4. **Deployment**: Single binary executable vs Python installation requirements

## License

Same as parent project.
