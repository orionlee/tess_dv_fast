"""TCE Statistics Utilities."""

from scipy.stats import chi2, norm

# The threshold of weak secondary (in MES) that is considered significant
# see: https://exoplanetarchive.ipac.caltech.edu/docs/DVSummaryPageCompanion_q1_q16.html
TCESTATS_WARN_THRESHOLD_WS_MAMMES = 7.1

# The threshold for odd-even depth difference (in sigma) that is considered significant
TCESTATS_WARN_THRESHOLD_OEDP_SIGMA = 3


def is_weak_secondary_significant(ws_maxmes_vals):
    return ws_maxmes_vals > TCESTATS_WARN_THRESHOLD_WS_MAMMES


def tce_bin_oedp_stat_to_percentile_sigma(stat):
    """
    Convert tce_bin_oedp_stat in TESS TCE CSVs to the signficance percentile and sigma shown in the TESS DV PDFs.

    The pipeline stores the odd-even depth comparison as a chi²(1) variate:
        stat = (d_odd - d_even)² / (σ_odd² + σ_even²)  (eq 5 of Twicken+ 2018)
                                    ^^^ or maybe σ_all² ?!

    It then reports in the DV PDFs a:
      - percentile = (1 - chi2.cdf(stat, 1)) * 100
                   = upper-tail p-value of χ²(1) × 100
      - sigma      = norm.ppf(1 - p/2)   [two-tailed equivalent Gaussian sigma]

    Note:
      - 100% / 0 sigma means there is no odd-even difference.
      - 0% / large sigma means there is significant odd-even difference.
      - intiutively, the tce_bin_oedp_stat value describes how large
        the differnce in depth is relative to the uncertainty in depth
        (not in strict linear proportion, but in squared values)
      - a stat value of 9 corresponds to a significance of 0.3% / 3 sigma
    """
    # treating the tce_bin_oedp_stat as chi2(1) variate is based on
    # Steffen+ 2010 paper, Section 3.2
    #   https://ui.adsabs.harvard.edu/abs/2010ApJ...725.1226S/abstract
    # Twicken+ 2018 , Section 3.3
    #   https://ui.adsabs.harvard.edu/abs/2018PASP..130f4502T/abstract
    # Conversion of the stat to significance % / sigma is described at
    #   https://exoplanetarchive.ipac.caltech.edu/docs/DVSummaryPageCompanion_q1_q16.html#F

    p = 1 - chi2.cdf(
        stat, df=1
    )  # upper-tail χ²(1) p-value, probably eq 6 of Twicken+ 2018
    percentile = p * 100
    sigma = norm.ppf(1 - p / 2)
    return percentile, sigma


def is_odd_even_depth_diff_significant(oedp_stat_vals):
    percentile, sigma = tce_bin_oedp_stat_to_percentile_sigma(oedp_stat_vals)
    return sigma > TCESTATS_WARN_THRESHOLD_OEDP_SIGMA
