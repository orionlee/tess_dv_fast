package common

import (
	"fmt"
	"html"
	"regexp"
	"strconv"
	"strings"
)

// Physical constants
const RJupiterToREarth = 71492.0 / 6378.1
const REarthToRJupiter = 6378.1 / 71492.0

// FormatExoMastID formats exomast_id as a clickable link
func FormatExoMastID(idStr string) string {
	re := regexp.MustCompile(`TIC\d+`)
	shortName := strings.ToLower(re.ReplaceAllString(idStr, ""))
	return fmt.Sprintf(
		`<a target="_exomast" href="https://exo.mast.stsci.edu/exomast_planet.html?planet=%s">%s</a>`,
		html.EscapeString(idStr),
		html.EscapeString(shortName),
	)
}

// FormatOffsetNSigma formats TicOffset / OotOffset as value (sigma) with color coding
func FormatOffsetNSigma(valSigmaStr string) string {
	// Special case: TCE has no offset
	if valSigmaStr == "0.0|-0.0" {
		return "N/A"
	}

	parts := strings.Split(valSigmaStr, "|")
	if len(parts) != 2 {
		return html.EscapeString(valSigmaStr)
	}

	val, err1 := strconv.ParseFloat(parts[0], 64)
	sigma, err2 := strconv.ParseFloat(parts[1], 64)

	if err1 != nil || err2 != nil {
		return html.EscapeString(valSigmaStr)
	}

	sigmaStyle := ""
	if sigma >= 3 {
		sigmaStyle = ` style="color: red; font-weight: bold;"`
	}

	return fmt.Sprintf("%.0f <span%s>(%.1f)</span>", val, sigmaStyle, sigma)
}

// FormatCodes formats codes as a clickable text input field
func FormatCodes(codes string) string {
	return fmt.Sprintf(
		`<input type="text" style="margin-left: 3ch; font-size: 90%%; color: #666; width: 10ch;" onclick="this.select();" readonly value='%s'>`,
		html.EscapeString(codes),
	)
}

// FormatProductURL returns a formatter function for product links (dvs, dvm, dvr)
func FormatProductURL(filename, productURL string) string {
	// Extract last 10 chars of filename for display
	displayName := filename
	if len(filename) > 10 {
		displayName = filename[len(filename)-10:]
	}
	return fmt.Sprintf(
		`<a target="_blank" href="%s">%s</a>`,
		html.EscapeString(productURL),
		html.EscapeString(displayName),
	)
}

// AddHTMLColumnUnits adds HTML units to column headers in a styled dataframe table
func AddHTMLColumnUnits(html string) string {
	html = strings.Replace(html, ">Rp</th>", ">R<sub>p</sub><br>R<sub>j</sub></th>", 1)
	html = strings.Replace(html, ">Epoch</th>", ">Epoch<br>BTJD</th>", 1)
	html = strings.Replace(html, ">Duration</th>", ">Duration<br>hr</th>", 1)
	html = strings.Replace(html, ">Period</th>", ">Period<br>day</th>", 1)
	html = strings.Replace(html, ">Depth</th>", ">Depth<br>%</th>", 1)
	html = strings.Replace(html, ">TicOffset</th>", ">TicOffset<br>\" (σ)</th>", 1)
	html = strings.Replace(html, ">OotOffset</th>", ">OotOffset<br>\" (σ)</th>", 1)
	return html
}
