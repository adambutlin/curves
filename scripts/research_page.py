"""The research page ``output/2026_treasury_selloff.html``, built from ``output/data/`` only.

Every number on the page is computed here from the tables (none is typed into the text),
and the same numbers are written to ``output/data/headline_numbers.json`` so that the README
and the brief can be checked against them. The page is self-contained: inline CSS, inline
SVG figures, and a small script for the interactive version of Figure 1.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

import research_figures as rf

MINUS = "−"
FULL = "30 Dec 2025 to 5 Oct 2026"


# ---------------------------------------------------------------- number formatting
def bp(x: float, sign: bool = True) -> str:
    r = int(np.round(x))
    s = f"{abs(r)}"
    if r < 0:
        return MINUS + s
    return ("+" + s) if (sign and r > 0) else s


def num(x: float) -> str:
    return bp(x, sign=False)


def rng(lo: float, hi: float) -> str:
    a, b = num(lo), num(hi)
    return f"{a}–{b}" if np.round(lo) >= 0 else f"{a} to {b}"


def pct(p: float) -> str:
    return f"{100 * p:.0f}%"


def numbers(d: dict) -> dict:
    dec = d["dec"].set_index(["maturity", "window"])
    acm = d["acm"].set_index(["maturity", "series"])
    mon = d["mon"]
    fit = d["fit"].set_index("maturity")
    fc = d["fc"]
    sig = d["sig"]
    rec = d["rec"]
    n = {}
    for mat in ("2y", "5y", "10y", "30y", "2s10s", "10s30s"):
        r = dec.loc[(mat, FULL)]
        k = mat
        n[f"{k}_actual"] = bp(r["actual_bp"])
        for c, short in (("us_news", "us"), ("global_risk", "gl"), ("euro_area", "ea"), ("unspanned", "un"),
                         ("all_shocks", "all"), ("us_macro", "mac"), ("us_monetary", "mon")):
            n[f"{k}_{short}_mt"] = bp(r[f"{c}_mt"])
            n[f"{k}_{short}_med"] = bp(r[f"{c}_p50"])
            n[f"{k}_{short}_rng"] = rng(r[f"{c}_p05"], r[f"{c}_p95"])
        n[f"{k}_p_us_largest"] = pct(r["p_us_largest"])
        n[f"{k}_p_macro"] = pct(r["p_macro_gt_monetary"])
        if mat in ("2y", "5y", "10y", "30y"):
            n[f"{k}_p_us_half"] = pct(r["p_us_more_than_half"])
    r10 = dec.loc[("10y", FULL)]
    n["10y_us_share_med"] = pct(r10["us_news_p50"] / r10["actual_bp"])
    for w, key in (("30 Dec 2025 to 27 Feb 2026", "w1"), ("27 Feb to 19 Aug 2026", "w2"), ("19 Aug to 5 Oct 2026", "w3")):
        for mat in ("2y", "10y"):
            r = dec.loc[(mat, w)]
            n[f"{mat}_{key}_actual"] = bp(r["actual_bp"])
            n[f"{mat}_{key}_us_mt"] = bp(r["us_news_mt"])
            n[f"{mat}_{key}_us_med"] = bp(r["us_news_p50"])
            n[f"{mat}_{key}_us_rng"] = rng(r["us_news_p05"], r["us_news_p95"])
            n[f"{mat}_{key}_un_med"] = bp(r["unspanned_p50"])
            n[f"{mat}_{key}_p_us_largest"] = pct(r["p_us_largest"])
    for mat in ("2y", "10y"):
        for s, short in (("ACM fitted yield", "fit"), ("ACM expected short rates", "rn"), ("ACM term premium", "tp")):
            r = acm.loc[(mat, s)]
            n[f"acm{mat}_{short}"] = bp(r["actual_bp"])
            n[f"acm{mat}_{short}_un_med"] = bp(r["unspanned_p50"])
            n[f"acm{mat}_{short}_un_rng"] = rng(r["unspanned_p05"], r["unspanned_p95"])
            n[f"acm{mat}_{short}_us_mt"] = bp(r["us_news_mt"])
    n["acm10y_rn_share"] = pct(acm.loc[("10y", "ACM expected short rates"), "actual_bp"]
                               / acm.loc[("10y", "ACM fitted yield"), "actual_bp"])
    for mat in ("2y", "10y"):
        g = mon[mon.maturity == mat].set_index("month")
        for m in g.index:
            tag = pd.Period(m).strftime("%b").lower()
            n[f"{mat}_{tag}_actual"] = bp(g.loc[m, "actual_bp"])
            n[f"{mat}_{tag}_un_mt"] = bp(g.loc[m, "unspanned_mt"])
            n[f"{mat}_{tag}_us_mt"] = bp(g.loc[m, "us_news_mt"])
            n[f"{mat}_{tag}_p_us_largest"] = pct(g.loc[m, "p_us_largest"])
    n["r2_2026_lo"] = pct(fit["r2_daily_2026"].min())
    n["r2_2026_hi"] = pct(fit["r2_daily_2026"].max())
    for mat in ("2y", "5y", "10y", "30y"):
        n[f"r2_{mat}_in"] = pct(fit.loc[mat, "r2_daily_2007_2025"])
        n[f"r2_{mat}_26"] = pct(fit.loc[mat, "r2_daily_2026"])
    nc = fc[(fc.measured_from == "next close")]
    rt = nc[nc.period == "2012-2025 real time"]
    n["cw_min"] = f"{rt['cw_p_origin_vs_curve_state'].min():.2f}"
    n["oos_best_rt"] = f"{100 * rt[['r2_own_move', 'r2_curve_state', 'r2_origin', 'r2_all_innovations']].max().max():.1f}%"
    n["oos_worst_rt"] = f"{100 * rt['r2_origin'].min():.0f}%".replace("-", MINUS)
    n["oos_best_2026"] = f"{100 * nc[nc.period == '2026 frozen model'][['r2_own_move', 'r2_curve_state', 'r2_origin', 'r2_all_innovations']].max().max():.1f}%"
    art = fc[(fc.measured_from == "same close") & (fc.maturity == "10y") & (fc.period == "2012-2025 real time")].iloc[0]
    n["artefact_r2"] = f"+{100 * art['r2_origin']:.1f}%"
    n["artefact_p"] = "< 0.001" if art["cw_p_origin_vs_curve_state"] < 0.001 else f"{art['cw_p_origin_vs_curve_state']:.3f}"
    st = sig.groupby("shock")["p_steepens_2s10s"].first()
    n["steep_min_us_global"] = pct(st[["us_monetary", "us_macro", "global_risk"]].min())
    n["steep_us_mon"], n["steep_us_mac"], n["steep_gl"] = (pct(st["us_monetary"]), pct(st["us_macro"]),
                                                           pct(st["global_risk"]))
    n["rec_us_share_ea"] = pct(rec["us_share_of_euro_rate_variance"])
    n["rec_events_mt"] = f"{rec['events_hit_median_target']} of {rec['events']}"
    n["rec_events_mean"] = pct(rec["events_mean_share_of_draws_hit"])
    n["rec_acceptance"] = f"{100 * rec['acceptance_rate']:.1f}%"
    n["rec_days"] = f"{rec['sample'][2]:,}"
    n["rec_us10_us"] = pct(rec["us10_variance_shares"]["us"])
    n["rec_us10_gl"] = pct(rec["us10_variance_shares"]["global"])
    n["rec_us10_ea"] = pct(rec["us10_variance_shares"]["ea"])
    ctx = d["ctx"].set_index("series")
    for mat in ("2y", "5y", "10y", "30y"):
        r = ctx.loc[f"{mat} Treasury yield, H.15 (%)"]
        n[f"h15_{mat}_start"] = f"{r['start_close']:.2f}%"
        n[f"h15_{mat}_end"] = f"{r['close_5oct2026']:.2f}%"
        n[f"h15_{mat}_from_dec31"] = bp(100 * (r["close_5oct2026"] - r["close_31dec2025"]))
        n[f"h15_{mat}_low"] = f"{r['low_2026']:.2f}%"
        n[f"h15_{mat}_high"] = f"{r['high_2026']:.2f}%"
    spx = ctx.loc["S&P 500 index"]
    n["spx_change"] = f"{100 * (spx['close_5oct2026'] / spx['start_close'] - 1):.0f}%"
    daily = d["daily"]
    n["days_2026"] = f"{len(daily) - 1}"
    r = dec.loc[("10y", FULL)]
    n["10y_us_width"] = num(r["us_news_p95"] - r["us_news_p05"])
    low = pd.Timestamp(daily.loc[daily["actual"].idxmin(), "date"])
    n["low_date"] = f"{low.day} {low.strftime('%B')}"
    n["low_level"] = bp(daily["actual"].min())
    base = list(n.items())
    n.update({f"{k}_u": v.lstrip("+") for k, v in base})                 # no plus sign, for prose
    n.update({f"{k}_abs": v.lstrip("+").lstrip(MINUS) for k, v in base})  # magnitude, for prose
    return n


# ---------------------------------------------------------------- tables
def table(df: pd.DataFrame, headers: list[str], caption: str, num_cols: int = 1) -> str:
    th = "".join(f'<th scope="col"{" class=num" if i >= num_cols else ""}>{h}</th>' for i, h in enumerate(headers))
    rows = []
    for _, r in df.iterrows():
        cells = []
        for i, v in enumerate(r):
            cls = ' class="num"' if i >= num_cols else ""
            tag = "th scope=\"row\"" if i == 0 else "td"
            cells.append(f"<{tag}{cls}>{v}</{tag.split()[0]}>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (f'<details class="tableview"><summary>{caption}</summary><div class="tablewrap"><table>'
            f"<thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></details>")


def tables(d: dict) -> dict:
    dec, mon, fit, fc = d["dec"], d["mon"], d["fit"], d["fc"]
    full = dec[dec.window == FULL].set_index("maturity")
    out = {}

    def cell(r, c):
        return f"{bp(r[c + '_mt'])} <span class=rng>({bp(r[c + '_p50'])}; {rng(r[c + '_p05'], r[c + '_p95'])})</span>"

    rows = []
    for mat in ("2y", "5y", "10y", "30y", "2s10s", "10s30s"):
        r = full.loc[mat]
        rows.append([rf.MATURITY_NAME[mat], bp(r["actual_bp"]), cell(r, "us_news"), cell(r, "global_risk"),
                     cell(r, "euro_area"), cell(r, "unspanned")])
    out["curve"] = table(pd.DataFrame(rows), ["", "Actual", "US news", "Global risk sentiment", "Euro-area news",
                                               "Unspanned"],
                         "Table: contributions by maturity, bp (median-target model; in brackets the median and "
                         "5–95% range across admissible models)")
    rows = []
    for w in ("30 Dec 2025 to 27 Feb 2026", "27 Feb to 19 Aug 2026", "19 Aug to 5 Oct 2026", FULL):
        r = dec[(dec.maturity == "10y") & (dec.window == w)].iloc[0]
        rows.append([w + (" (whole period)" if w == FULL else ""), bp(r["actual_bp"]),
                     cell(r, "us_news"), cell(r, "global_risk"), cell(r, "euro_area"), cell(r, "unspanned"),
                     pct(r["p_us_largest"])])
    out["phases"] = table(pd.DataFrame(rows), ["10-year", "Actual", "US news", "Global risk sentiment",
                                                "Euro-area news", "Unspanned", "US news largest"],
                          "Table: the 10-year by phase, bp (median-target model; in brackets the median and "
                          "5–95% range across admissible models)")
    rows = []
    for mat in ("10y", "2y"):
        g = mon[mon.maturity == mat]
        for _, r in g.iterrows():
            rows.append([f"{rf.MATURITY_NAME[mat]}, {pd.Period(r['month']).strftime('%b')}", bp(r["actual_bp"]),
                         bp(r["us_news_mt"]), bp(r["global_risk_mt"]), bp(r["euro_area_mt"]), bp(r["unspanned_mt"]),
                         pct(r["p_us_largest"]), pct(r["p_global_largest"]), pct(r["p_euro_largest"])])
    out["monthly"] = table(pd.DataFrame(rows), ["Month", "Actual", "US news", "Global risk", "Euro area", "Unspanned",
                                                 "US largest", "Global largest", "Euro area largest"],
                           "Table: monthly contributions, bp (median-target model), and the share of admissible "
                           "models in which each origin is the largest")
    rows = []
    for mat in ("10y", "2y"):
        r = full.loc[mat]
        for c in ("all_shocks", "unspanned", "us_news", "global_risk", "euro_area", "us_macro", "us_monetary"):
            rows.append([f"{rf.MATURITY_NAME[mat]}: {rf.LABEL[c]}", bp(r[c + "_p50"]),
                         rng(r[c + "_p05"], r[c + "_p95"]), bp(r[c + "_mt"])])
    out["uncertainty"] = table(pd.DataFrame(rows), ["Contribution, 30 Dec 2025 to 5 Oct 2026", "Median", "5–95%",
                                                     "Median-target model"],
                               "Table: contributions across the 1,000 admissible models, bp")
    rows = []
    f = fit.set_index("maturity")
    for mat in ("2y", "5y", "10y", "30y"):
        rows.append([rf.MATURITY_NAME[mat], pct(f.loc[mat, "r2_daily_2007_2025"]), pct(f.loc[mat, "r2_daily_2026"]),
                     f"{f.loc[mat, 'rmse_daily_2026_bp']:.1f}", f"{f.loc[mat, 'sd_daily_2026_bp']:.1f}"])
    fit_t = table(pd.DataFrame(rows), ["", "Daily R² 2007–2025", "Daily R² 2026", "RMSE 2026, bp",
                                        "s.d. of daily change 2026, bp"],
                  "Table: explanatory fit of the frozen loadings")
    rows = []
    g = fc[(fc.measured_from == "next close")]
    for per in ("2012-2025 real time", "2026 frozen model"):
        for mat in ("2y", "5y", "10y", "30y"):
            for h in (1, 5, 20):
                r = g[(g.period == per) & (g.maturity == mat) & (g.horizon_days == h)].iloc[0]
                rows.append([f"{rf.MATURITY_NAME[mat]}, {h}d, {per.replace('-', chr(8211))}",
                             f"{100 * r['r2_own_move']:.1f}", f"{100 * r['r2_curve_state']:.1f}",
                             f"{100 * r['r2_origin']:.1f}", f"{r['cw_p_origin_vs_curve_state']:.2f}"])
    fc_t = table(pd.DataFrame(rows).replace({"-": MINUS}, regex=True),
                 ["Maturity, horizon, period", "Own move", "Plus curve state", "Plus origin of news",
                  "Clark–West p, origin"],
                 "Table: out-of-sample R² against a no-change forecast, %, from the next close")
    out["forecast"] = fit_t + fc_t
    return out


# ---------------------------------------------------------------- page
def build(data: Path, out_html: Path) -> None:
    d = rf.load(data)
    d["acm"] = pd.read_csv(data / "acm_comparison_2026.csv")
    d["sig"] = pd.read_csv(data / "curve_signatures.csv")
    d["rec"] = json.loads((data / "model_record.json").read_text())
    d["ctx"] = pd.read_csv(data / "market_context_2026.csv")
    n = numbers(d)
    (data / "headline_numbers.json").write_text(json.dumps(n, indent=1, ensure_ascii=False))
    t = tables(d)
    figs = rf.figures(d, standalone=False)
    svg = {name: rf.svg_string(fig, f"f{i + 1}") for i, (name, fig) in enumerate(figs.items())}
    daily = d["daily"]
    series = {"date": list(daily["date"]), "actual": daily["actual"].round(1).tolist(),
              "us": daily["us_news"].round(1).tolist(), "gl": daily["global_risk"].round(1).tolist(),
              "ea": daily["euro_area"].round(1).tolist(), "un": daily["unspanned"].round(1).tolist(),
              "us05": daily["us_news_p05"].round(1).tolist(), "us95": daily["us_news_p95"].round(1).tolist()}
    page = TEMPLATE
    for k, v in n.items():
        page = page.replace(f"%%{k}%%", html.escape(v, quote=False))
    for k, v in t.items():
        page = page.replace(f"%%table_{k}%%", v)
    for k, v in svg.items():
        page = page.replace(f"%%svg_{k}%%", v)
    page = page.replace("%%DAILY_JSON%%", json.dumps(series, separators=(",", ":")))
    for k, v in rf.TITLES.items():
        page = page.replace(f"%%title_{k}%%", html.escape(v))
    left = [s for s in page.split("%%")[1::2] if s and " " not in s and len(s) < 40]
    if left:
        raise KeyError(f"unfilled placeholders: {sorted(set(left))}")
    out_html.write_text(page, encoding="utf-8")
    print(f"page: wrote {out_html.name} ({len(page) / 1e3:.0f} kB)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What drove the 2026 Treasury selloff?</title>
<meta name="description" content="A structural cross-asset decomposition of the 2026 rise in US Treasury yields, using a sign-identified Bayesian VAR frozen at end-2025.">
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --rule: rgba(11, 11, 11, 0.10);
  --us: #2a78d6; --gl: #eb6834; --ea: #1baf7a; --un: #b3b1a9;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
  --sans: system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--page); color: var(--ink); }
body { font: 17px/1.62 var(--serif); -webkit-text-size-adjust: 100%; }
main { max-width: 740px; margin: 0 auto; padding: 56px 16px 72px; }
h1, h2, h3, .kicker, .dek, .byline, .stat, figure, .tableview, .eq-note, nav, footer, table { font-family: var(--sans); }
.kicker { text-transform: uppercase; letter-spacing: 0.08em; font-size: 12.5px; color: var(--muted); margin: 0 0 10px; font-weight: 600; }
h1 { font-size: clamp(30px, 5vw, 42px); line-height: 1.12; margin: 0 0 14px; letter-spacing: -0.01em; }
.dek { font-size: 18.5px; line-height: 1.45; color: var(--ink2); margin: 0 0 14px; }
.byline { font-size: 14px; color: var(--muted); margin: 0 0 30px; }
h2 { font-size: 22px; line-height: 1.25; margin: 52px 0 12px; }
h3 { font-size: 16px; margin: 28px 0 8px; }
p { margin: 0 0 16px; }
a { color: #1c5cab; }
.lead { font-size: 19px; line-height: 1.55; border-top: 2px solid var(--ink); padding-top: 18px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 26px 0 8px; }
.stat { background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 14px 14px 12px; }
.stat .v { font-size: 27px; font-weight: 650; line-height: 1.1; }
.stat .l { font-size: 13px; line-height: 1.35; color: var(--ink2); margin-top: 6px; }
figure { margin: 30px calc(50% - min(490px, 50vw - 16px)); }
.figtitle { font-size: 16px; font-weight: 650; margin: 0 0 4px; }
.fignum { color: var(--muted); font-weight: 600; margin-right: 6px; }
.chart { background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 10px 10px 4px; overflow-x: auto; }
.chart svg { display: block; width: 100%; height: auto; min-width: 600px; }
figcaption { font-size: 13.5px; line-height: 1.45; color: var(--ink2); margin-top: 8px; max-width: 760px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 13px; color: var(--ink2); margin: 4px 0 6px; }
.legend span { display: inline-flex; align-items: center; gap: 7px; }
.key { width: 18px; height: 3px; border-radius: 2px; display: inline-block; }
.key.band { height: 10px; opacity: 0.35; }
#fig1-chart { position: relative; outline: none; }
#fig1-chart:focus-visible { box-shadow: 0 0 0 2px var(--us); border-radius: 6px; }
#fig1-chart svg { min-width: 0; }
#fig1-chart .tick { font: 12px var(--sans); fill: var(--ink2); font-variant-numeric: tabular-nums; }
#fig1-chart .note { font: 12px var(--sans); fill: var(--ink2); }
#fig1-chart .endlab { font: 12.5px var(--sans); fill: var(--ink); }
#fig1-chart .endlab.strong { font-weight: 650; }
#fig1-chart .endsub { font: 11.5px var(--sans); fill: var(--ink2); }
.tip { position: absolute; pointer-events: none; background: #fff; border: 1px solid var(--rule); border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08); padding: 9px 11px; font: 12.5px/1.45 var(--sans); min-width: 210px; display: none; z-index: 2; }
.tip .d { font-weight: 650; margin-bottom: 4px; }
.tip table { width: 100%; border-collapse: collapse; }
.tip td { padding: 1px 0; }
.tip td.n { text-align: right; font-variant-numeric: tabular-nums; padding-left: 12px; }
.tip .sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.tip .sub td { color: var(--ink2); font-size: 11.5px; padding-left: 16px; }
.hint { font-size: 12.5px; color: var(--muted); margin: 6px 0 0; }
.tableview { margin: 10px 0 26px; font-size: 14px; }
.tableview summary { cursor: pointer; color: var(--ink2); font-size: 13.5px; }
.tablewrap { overflow-x: auto; margin-top: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; background: var(--surface); }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--grid); vertical-align: top; }
thead th { font-weight: 650; color: var(--ink2); border-bottom: 1px solid var(--axis); }
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.rng { color: var(--muted); font-size: 12px; }
.eq { font-family: var(--serif); font-size: 18px; text-align: center; margin: 14px 0 16px; overflow-x: auto; white-space: nowrap; }
.eq var { font-style: italic; }
.eq-note { font-size: 14px; color: var(--ink2); }
.restrict td, .restrict th { text-align: center; }
.restrict th[scope=row] { text-align: left; }
.restrict .p { color: var(--us); font-weight: 700; }
.restrict .m { color: #d03b3b; font-weight: 700; }
ol.refs { padding-left: 20px; font-size: 15px; }
ol.refs li { margin-bottom: 8px; }
.callout { background: var(--surface); border-left: 3px solid var(--ink); padding: 12px 16px; margin: 20px 0; font-size: 16px; }
footer { border-top: 1px solid var(--axis); margin-top: 56px; padding-top: 16px; font-size: 13.5px; color: var(--ink2); }
footer code { font-size: 12.5px; }
@media (max-width: 720px) {
  body { font-size: 16.5px; }
  main { padding-top: 32px; }
  .stats { grid-template-columns: repeat(2, 1fr); }
}
@media print {
  body { background: #fff; }
  figure { margin: 24px 0; }
  .chart svg { min-width: 0; }
  details { display: block; }
}
</style>
</head>
<body>
<main>
<header>
<p class="kicker">Research note · October 2026</p>
<h1>What drove the 2026 Treasury selloff?</h1>
<p class="dek">A structural cross-asset decomposition of the US Treasury curve, from a Bayesian VAR identified with sign restrictions (Brandt et al., 2021), frozen at end-2025 and applied to 2026 without re-estimation.</p>
<p class="byline">Adam Butlin · Data to 5 October 2026 · <a href="https://github.com/adambutlin/curves">Code and data</a></p>
</header>

<p class="lead">Between the closes of 30 December 2025 and 5 October 2026 the 10-year Treasury yield rose %%10y_actual_u%%bp and the 2-year %%2y_actual_u%%bp. At the long end, the rise was news that also moved equities, the dollar and euro-area rates, and US news was its largest source in %%10y_p_us_largest%% of admissible models (median %%10y_us_med_u%%bp of the 10-year's rise). The front end was different: about %%2y_un_med_u%%bp of the 2-year's rise was a repricing of the expected policy path that no cross-asset shock explains, and that repricing accounts for the whole of the curve's bear flattening. The decomposition explains most of each day's move but has no value for forecasting the next.</p>

<div class="stats">
  <div class="stat"><div class="v">%%10y_actual%%bp</div><div class="l">10-year Treasury yield, 30 Dec 2025 to 5 Oct 2026</div></div>
  <div class="stat"><div class="v">%%10y_us_med_u%%bp</div><div class="l">from US news: median of admissible models (5–95%: %%10y_us_rng%%bp)</div></div>
  <div class="stat"><div class="v">%%2y_un_med_u%%bp</div><div class="l">of the 2-year's %%2y_actual_u%%bp rise not explained by any cross-asset shock (%%2y_un_rng%%bp)</div></div>
  <div class="stat"><div class="v">0 of 12</div><div class="l">maturity–horizon pairs at which knowing the shock improves on a no-change forecast</div></div>
</div>

<h2 id="decomposition">1. The 10-year: US news, plus a lift from risk sentiment</h2>
<p>Yields fell into late February: by the %%low_date%% low the 10-year was %%low_level%%bp on the year, mostly on weaker US news. They then rose in three steps, in March, July and, most sharply, September (%%10y_sep_actual%%bp). In the representative model (the median-target model of Fry and Pagan, the single admissible model closest to the median impulse responses), US news accounts for %%10y_us_mt_u%%bp of the %%10y_actual_u%%bp rise, improving global risk sentiment for %%10y_gl_mt_u%%bp, and euro-area news for almost nothing (%%10y_ea_mt%%bp). A positive risk-sentiment contribution means risk appetite improved: the safe-haven demand for Treasuries unwound and yields rose. Together the five shocks leave essentially none of the 10-year's rise unexplained.</p>
<p>Across all admissible models the 5–95% range of the US contribution is %%10y_us_rng%%bp, with a median of %%10y_us_med_u%%bp. Its sign is certain; its size is not.</p>

<figure>
  <div class="figtitle"><span class="fignum">Figure 1</span>%%title_fig1_10y_decomposition%%</div>
  <div class="legend" aria-hidden="true">
    <span><i class="key" style="background:#0b0b0b"></i>Actual 10-year yield</span>
    <span><i class="key" style="background:var(--us)"></i>US news <i class="key band" style="background:var(--us)"></i>5–95% of admissible models</span>
    <span><i class="key" style="background:var(--gl)"></i>Global risk sentiment</span>
    <span><i class="key" style="background:var(--ea)"></i>Euro-area news</span>
    <span><i class="key" style="background:var(--un)"></i>Unspanned (curve-specific news)</span>
  </div>
  <div class="chart"><div id="fig1-chart" tabindex="0" aria-label="Cumulative 10-year yield change and its decomposition through 2026. Use the left and right arrow keys to move through the days."></div></div>
  <p class="hint">Hover, or focus the chart and use the arrow keys, to read the values on any day.</p>
  <figcaption>Cumulative change in the 10-year H.15 yield since the close of 30 December 2025 and the contributions of the identified shocks in the median-target model, in basis points. The shaded band is the 5–95% range of the US-news contribution across the 1,000 admissible models. Vertical lines mark the pre-registered window boundaries. The window starts on 30 December because Eurex, where the model's euro-area equity future trades, was closed on 31 December; measured from the 31 December close the 10-year rose %%h15_10y_from_dec31_u%%bp.</figcaption>
</figure>
%%table_phases%%

<h2 id="curve">2. Across the curve: the same news at the long end, a policy repricing at the front</h2>
<p>At 5, 10 and 30 years the cross-asset shocks account for nearly all of the rise. At 2 years they account for only about half: %%2y_un_med_u%%bp of the %%2y_actual_u%%bp (%%2y_un_rng%%bp across admissible models) is news that moved the 2-year without the equity, currency and euro-area signature of any identified shock. The NY Fed's term-structure model (Adrian, Crump and Moench) places that part in expected short rates rather than in the term premium: %%acm2y_rn_un_med_u%%bp of the 2-year's %%acm2y_rn_u%%bp rise in expected rates is unspanned, against %%acm2y_tp_un_med%%bp of its %%acm2y_tp_u%%bp rise in the term premium. It is a repricing of the expected path of the federal funds rate, the kind of news carried by data releases and Fed communication that markets price mainly at the front end.</p>
<p>Every identified shock steepens the curve when it raises yields: its 10-year loading exceeds its 2-year loading in at least %%steep_min_us_global%% of admissible models for the US and global shocks. The cross-asset news therefore steepened 2s10s, by %%2s10s_all_med_u%%bp (%%2s10s_all_rng%%), and the %%2s10s_actual_abs%%bp bear flattening came entirely from the unspanned front-end repricing (%%2s10s_un_med%%bp; %%2s10s_un_rng%%). At the long end, 10s30s flattened by %%10s30s_actual_abs%%bp, partly because US news moves 5- to 10-year yields most (%%10s30s_us_mt%%bp) and partly through unspanned news (%%10s30s_un_med%%bp).</p>

<figure>
  <div class="figtitle"><span class="fignum">Figure 2</span>%%title_fig2_curve%%</div>
  <div class="chart">%%svg_fig2_curve%%</div>
  <figcaption>Contributions to each yield and slope between the closes of 30 December 2025 and 5 October 2026 in the median-target model; the diamond is the actual change. The unspanned part does not depend on the sign restrictions.</figcaption>
</figure>
%%table_curve%%

<h2 id="timing">3. When it happened: three up-legs, each led by US news</h2>
<p>The selloff was not one move. At the 10-year it came in March (%%10y_mar_actual%%bp; US news the largest origin in %%10y_mar_p_us_largest%% of admissible models), July (%%10y_jul_actual%%bp; %%10y_jul_p_us_largest%%) and September (%%10y_sep_actual%%bp; %%10y_sep_p_us_largest%%). The dominant driver did not change: US news led every leg. In the quiet months the small moves are attributed mainly to risk sentiment in the representative model, but there the identification cannot tell global from euro-area news. At the 2-year the unspanned repricing came in the same bursts, adding %%2y_mar_un_mt%%bp in March, %%2y_jun_un_mt%%bp in June and %%2y_sep_un_mt%%bp in September.</p>

<figure>
  <div class="figtitle"><span class="fignum">Figure 3</span>%%title_fig3_monthly%%</div>
  <div class="chart">%%svg_fig3_monthly%%</div>
  <figcaption>Monthly contributions in the median-target model (January from the 30 December close, October to the 5th); dots are actual monthly changes. Percentages give the share of admissible models in which US news is the largest of the three origins.</figcaption>
</figure>
%%table_monthly%%

<h2 id="uncertainty">4. How certain is the attribution?</h2>
<p>Sign restrictions identify a set of models, not one: 1,000 rotations of the reduced form satisfy the restrictions and each is an equally admissible account of the same data. Figure 4 sorts the results by how much they depend on which rotation is right.</p>
<ul>
<li><strong>Identification-free.</strong> How much of a move is spanned by the cross-asset shocks does not depend on the restrictions at all. The 10-year's unspanned part is %%10y_un_med%%bp (%%10y_un_rng%%), the 2-year's %%2y_un_med_u%%bp (%%2y_un_rng%%).</li>
<li><strong>Robust in sign.</strong> US news raised yields at every maturity in every admissible model. It is the largest of the three origins in %%10y_p_us_largest%% of models at the 10-year and %%2y_p_us_largest%% at the 2-year, and accounts for more than half of the 10-year's rise in %%10y_p_us_half%%.</li>
<li><strong>Weakly identified.</strong> The remainder is split between global risk sentiment (median %%10y_gl_med_u%%bp, %%10y_gl_rng%%) and euro-area news (median %%10y_ea_med_u%%bp, %%10y_ea_rng%%) in proportions the data do not pin down. The representative model's zero for euro-area news lies at the bottom of the set, so "no euro-area contribution" is not a robust finding.</li>
<li><strong>Not pinned down.</strong> US macro news exceeds US monetary news in %%10y_p_macro%% of models. The two shocks differ only in the sign of the US equity response, and the data cannot tell whether the US news of 2026 was mainly about growth or about policy.</li>
</ul>

<figure>
  <div class="figtitle"><span class="fignum">Figure 4</span>%%title_fig4_identification%%</div>
  <div class="chart">%%svg_fig4_identification%%</div>
  <figcaption>Contributions to the change between 30 December 2025 and 5 October 2026 across the 1,000 admissible models: dot = median, line = 5–95% range, open diamond = the median-target model used in Figures 1–3.</figcaption>
</figure>
%%table_uncertainty%%

<h2 id="forecasting">5. Does knowing the cause predict what happens next?</h2>
<p>No. The loadings frozen at end-2025 explain %%r2_2026_lo%%–%%r2_2026_hi%% of the daily variance of 2026 yield changes, as much as in 2007–2025, so the structure was stable through the selloff. But in real-time forecasts over 2012–2025, with the VAR, the identification and the loadings re-estimated each year on past data only, adding the origin of today's news to the day's own move and the state of the curve never improves forecasts of the change over the next 1, 5 or 20 days (Clark–West p ≥ %%cw_min%% at every maturity and horizon), and no specification beats a no-change forecast. 2026 gives the same answer.</p>
<p>One apparent exception is an artefact. Measured from the same close, today's news "predicts" tomorrow's 10-year H.15 change (out-of-sample R² %%artefact_r2%%, p %%artefact_p%%). H.15 yields are recorded earlier in the New York afternoon than the market prices the model uses, so tomorrow's H.15 change contains the end of today's news. The effect disappears when the forecast starts at the next close, and it is not tradeable.</p>
<p class="callout">The decomposition is an attribution and state-classification tool, not a forecasting model. It says what kind of news moved yields, robustly at the level of origin, and nothing about where yields go next.</p>

<figure>
  <div class="figtitle"><span class="fignum">Figure 5</span>%%title_fig5_forecasting%%</div>
  <div class="chart">%%svg_fig5_forecasting%%</div>
  <figcaption>Left: share of the daily variance of each yield explained by the five shocks, with loadings frozen at end-2025. Right: real-time out-of-sample R² against a no-change forecast for the change over the next 1, 5 and 20 days, measured from the next close.</figcaption>
</figure>
%%table_forecast%%

<h2 id="method">Method</h2>
<p><strong>Model.</strong> Brandt et al.'s (2021) daily Bayesian VAR in five variables, recorded at or near the New York close: the 10-year euro-area OIS rate (EONIA, then €STR), the Euro Stoxx 50 future, the S&amp;P 500, the euro-dollar exchange rate and the euro-area minus US 10-year spread. Estimated on 2007–2025 (%%rec_days%% days) with four lags and a Minnesota prior (overall tightness 0.2):</p>
<p class="eq"><var>Y</var><sub><var>t</var></sub> = <var>c</var> + <var>A</var><sub>1</sub><var>Y</var><sub><var>t</var>−1</sub> + … + <var>A</var><sub>4</sub><var>Y</var><sub><var>t</var>−4</sub> + <var>u</var><sub><var>t</var></sub>, &nbsp;&nbsp; <var>u</var><sub><var>t</var></sub> = <var>B</var><var>ε</var><sub><var>t</var></sub>, &nbsp;&nbsp; E[<var>ε</var><sub><var>t</var></sub><var>ε</var><sub><var>t</var></sub>′] = <var>I</var>,</p>
<p class="eq-note">where <var>Y</var><sub><var>t</var></sub> holds the five daily changes, <var>u</var><sub><var>t</var></sub> the reduced-form innovations with covariance Σ, and <var>ε</var><sub><var>t</var></sub> the five structural shocks. The impact matrix <var>B</var> = chol(Σ)<var>Q</var> is identified only up to the orthogonal rotation <var>Q</var>.</p>
<p><strong>Identification.</strong> Sign restrictions on impact, exactly as in Brandt et al.'s Table 1. Rotations are drawn uniformly (Arias, Rubio-Ramírez and Waggoner, 2018) jointly with the reduced-form posterior until 1,000 satisfy the restrictions (%%rec_acceptance%% of candidates). The spread restriction identifies the country of origin: a domestic shock moves the domestic long rate by more than the foreign one.</p>
<div class="tablewrap"><table class="restrict">
<thead><tr><th scope="col">Response on impact to a positive shock</th><th scope="col">Euro-area monetary</th><th scope="col">Euro-area macro</th><th scope="col">US monetary</th><th scope="col">US macro</th><th scope="col">Global risk (risk-off)</th></tr></thead>
<tbody>
<tr><th scope="row">Euro-area 10-year OIS rate</th><td class="p">+</td><td class="p">+</td><td class="p">+</td><td class="p">+</td><td class="m">−</td></tr>
<tr><th scope="row">Euro Stoxx 50</th><td class="m">−</td><td class="p">+</td><td>·</td><td>·</td><td class="m">−</td></tr>
<tr><th scope="row">S&amp;P 500</th><td>·</td><td>·</td><td class="m">−</td><td class="p">+</td><td class="m">−</td></tr>
<tr><th scope="row">Euro against the dollar</th><td class="p">+</td><td class="p">+</td><td class="m">−</td><td class="m">−</td><td class="m">−</td></tr>
<tr><th scope="row">Euro-area minus US 10-year spread</th><td class="p">+</td><td class="p">+</td><td class="m">−</td><td class="m">−</td><td class="p">+</td></tr>
<tr><th scope="row"><em>Implied: US 10-year yield</em></th><td colspan="2"><em>rises less than the euro rate, or falls</em></td><td colspan="2"><em>rises more than the euro rate</em></td><td><em>falls more than the euro rate</em></td></tr>
</tbody></table></div>
<p class="eq-note">· = unrestricted. US monetary and US macro news both raise US yields and the dollar; they differ only in the sign of the S&amp;P 500 response, which is why the split between them is fragile. A positive global-risk shock is a flight to safety, so a negative one (improving sentiment) raises Treasury yields.</p>
<p><strong>The Treasury curve.</strong> The model contains one Treasury yield. The 2-, 5-, 10- and 30-year H.15 yields are attached by projecting each day's change on the five shocks and two lags, model by model, on 2007–2025 data:</p>
<p class="eq">Δ<var>y</var><sub><var>τ</var>,<var>t</var></sub> = <var>c</var><sub><var>τ</var></sub> + Σ<sub><var>k</var>=1</sub><sup>5</sup> Σ<sub><var>s</var>=0</sub><sup>2</sup> <var>θ</var><sub><var>τ</var>,<var>k</var>,<var>s</var></sub> <var>ε</var><sub><var>k</var>,<var>t</var>−<var>s</var></sub> + <var>e</var><sub><var>τ</var>,<var>t</var></sub>,</p>
<p class="eq-note">where Δ<var>y</var><sub><var>τ</var>,<var>t</var></sub> is the daily change in the <var>τ</var>-year yield. The lags credit the catch-up of H.15 yields, which are recorded before the New York close, to the shock that caused it. The contribution of shock <var>k</var> over a window <var>W</var> is Σ<sub><var>t</var>∈<var>W</var></sub> Σ<sub><var>s</var></sub> <var>θ</var><sub><var>τ</var>,<var>k</var>,<var>s</var></sub><var>ε</var><sub><var>k</var>,<var>t</var>−<var>s</var></sub>; the rest of the window's change is "unspanned": news the five cross-asset shocks do not represent. Because the span of the shocks does not depend on the rotation, neither does the unspanned part.</p>
<p><strong>Discipline.</strong> The model and the curve loadings were frozen at end-2025, hashed, and committed before any 2026 maturity data were read; the design was pre-registered. Nothing is re-estimated on 2026 data. On 2007–2025 the model reproduces Brandt et al.'s spillovers closely (US shocks explain %%rec_us_share_ea%% of the daily variance of the euro-area rate, against their 40%), and its median-target model attributes %%rec_events_mt%% of their dated events to the expected shock, although the average admissible model manages only %%rec_events_mean%%. In the full sample, US shocks account for %%rec_us10_us%% of the daily variance of the 10-year Treasury yield, global risk for %%rec_us10_gl%% and euro-area shocks for %%rec_us10_ea%%.</p>

<h2 id="limitations">Limitations</h2>
<ul>
<li><strong>Set identification.</strong> The 5–95% range of the US contribution to the 10-year spans %%10y_us_width%%bp. Robust statements concern the origin of the news and the unspanned front end; the macro/monetary split and the global/euro-area split are not robust.</li>
<li><strong>The representative model is not central on every dimension.</strong> The median-target model used in Figures 1–3 sits near the upper end of the US-news range and at the bottom of the euro-area range; the medians across models are reported beside it throughout.</li>
<li><strong>Timing.</strong> H.15 yields are recorded before the New York close; two lags in the projection handle this for attribution. LSEG benchmark yields at every maturity would remove the issue.</li>
<li><strong>Unspanned is not noise.</strong> It is news the five cross-asset shocks do not represent. Reading the front-end part as a policy-path repricing relies on the NY Fed's term-structure model, itself an estimate.</li>
<li><strong>Expectations versus term premium.</strong> Loadings estimated on 2007–2025, a sample in which the policy rate sat at its lower bound almost half the time, map cross-asset news mainly into the term premium; in 2026 the same news moved expected rates instead (the NY Fed's model puts %%acm10y_rn_share%% of the 10-year's rise in expected rates). A lower bound mutes the response of expected rates to news (Swanson and Williams, 2014), so any fixed mapping from this decomposition into expectations and premia is regime-dependent.</li>
<li><strong>Data.</strong> The five model variables are LSEG data recorded at the New York close and cannot be redistributed. The figures and this page are rebuilt from derived tables that are published with the code.</li>
</ul>

<h2 id="references">References</h2>
<ol class="refs">
<li>Brandt, L., Saint Guilhem, A., Schröder, M. and Van Robays, I. (2021). What drives euro area financial market developments? The role of US spillovers and global risk. ECB Working Paper No. 2560.</li>
<li>Arias, J. E., Rubio-Ramírez, J. F. and Waggoner, D. F. (2018). Inference based on structural vector autoregressions identified with sign and zero restrictions: theory and applications. <em>Econometrica</em>, 86(2), 685–720.</li>
<li>Fry, R. and Pagan, A. (2011). Sign restrictions in structural vector autoregressions: a critical review. <em>Journal of Economic Literature</em>, 49(4), 938–960.</li>
<li>Adrian, T., Crump, R. K. and Moench, E. (2013). Pricing the term structure with linear regressions. <em>Journal of Financial Economics</em>, 110(1), 110–138.</li>
<li>Clark, T. E. and West, K. D. (2007). Approximately normal tests for equal predictive accuracy in nested models. <em>Journal of Econometrics</em>, 138(1), 291–311.</li>
<li>Swanson, E. T. and Williams, J. C. (2014). Measuring the effect of the zero lower bound on medium- and longer-term interest rates. <em>American Economic Review</em>, 104(10), 3154–3185.</li>
</ol>

<footer>
<p>Data: LSEG (euro-area OIS, Euro Stoxx 50 future, euro-dollar, 10-year Treasury benchmark, all near the New York close); S&amp;P 500; Federal Reserve H.15 constant-maturity yields; Federal Reserve Bank of New York ACM term-structure estimates. Sample 2007–2025 for estimation; %%days_2026%% trading days of 2026 to 5 October. Every number on this page is computed from the derived tables in <code>output/data/</code>; rebuild with <code>python scripts/build_research_output.py</code>. Code, pre-registrations and audit trail: <a href="https://github.com/adambutlin/curves">github.com/adambutlin/curves</a>.</p>
</footer>
</main>

<script>
(function () {
  "use strict";
  var D = %%DAILY_JSON%%;
  var host = document.getElementById("fig1-chart");
  if (!host) return;
  var C = {actual: "#0b0b0b", us: "#2a78d6", gl: "#eb6834", ea: "#1baf7a", un: "#b3b1a9"};
  var NAME = {actual: "Actual", us: "US news", gl: "Global risk sentiment", ea: "Euro-area news", un: "Unspanned"};
  var NS = "http://www.w3.org/2000/svg";
  var T = D.date.map(function (s) { return Date.parse(s + "T00:00:00Z"); });
  var n = T.length, idx = n - 1, G = null, lastW = 0;
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var tip = document.createElement("div");
  tip.className = "tip";
  host.appendChild(tip);

  function el(name, attrs, parent) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function fmt(v) {
    var r = Math.round(v);
    return (r > 0 ? "+" : r < 0 ? "−" : "") + Math.abs(r);
  }
  function spread(vals, gap, lo) {
    var order = vals.map(function (v, i) { return i; }).sort(function (a, b) { return vals[a] - vals[b]; }).reverse();
    var pos = vals.slice(), prev = Infinity;
    order.forEach(function (i) { pos[i] = Math.min(vals[i], prev - gap); prev = pos[i]; });
    var shift = Math.max(0, lo - Math.min.apply(null, pos));
    return pos.map(function (p) { return p + shift; });
  }

  function draw() {
    var W = Math.max(300, Math.floor(host.clientWidth));
    if (W === lastW) return;
    lastW = W;
    var narrow = W < 640;
    var H = Math.round(Math.min(470, Math.max(290, W * 0.5)));
    var m = {l: narrow ? 38 : 50, r: narrow ? 12 : 196, t: 24, b: 30};
    var pw = W - m.l - m.r, ph = H - m.t - m.b;
    var yMin = -40, yMax = 135;
    var t0 = Date.parse("2025-12-27T00:00:00Z"), t1 = Date.parse("2026-10-08T00:00:00Z");
    function X(t) { return m.l + (t - t0) / (t1 - t0) * pw; }
    function Y(v) { return m.t + (yMax - v) / (yMax - yMin) * ph; }
    var old = host.querySelector("svg");
    if (old) host.removeChild(old);
    var svg = el("svg", {viewBox: "0 0 " + W + " " + H, width: W, height: H, "aria-hidden": "true"});
    host.insertBefore(svg, tip);
    for (var v = -40; v <= 120; v += 20) {
      el("line", {x1: m.l, x2: m.l + pw, y1: Y(v), y2: Y(v), stroke: v === 0 ? "#c3c2b7" : "#e1e0d9", "stroke-width": 1}, svg);
      el("text", {x: m.l - 7, y: Y(v) + 4, "text-anchor": "end", "class": "tick"}, svg).textContent = v < 0 ? "−" + (-v) : String(v);
    }
    for (var k = 0; k < 10; k++) {
      if (narrow && k % 2) continue;
      el("text", {x: X(Date.UTC(2026, k, 1)), y: m.t + ph + 20, "text-anchor": "middle", "class": "tick"}, svg).textContent = MONTHS[k];
    }
    [["2026-02-27", "27 Feb: yields at their 2026 low"], ["2026-08-19", "19 Aug: second leg"]].forEach(function (a) {
      var x = X(Date.parse(a[0] + "T00:00:00Z"));
      el("line", {x1: x, x2: x, y1: m.t, y2: m.t + ph, stroke: "#c3c2b7", "stroke-width": 1}, svg);
      el("text", {x: x + 5, y: m.t + 11, "class": "note"}, svg).textContent = narrow ? a[0].slice(8) + (a[0].slice(5, 7) === "02" ? " Feb" : " Aug") : a[1];
    });
    var band = "", i;
    for (i = 0; i < n; i++) band += (i ? "L" : "M") + X(T[i]).toFixed(1) + "," + Y(D.us95[i]).toFixed(1);
    for (i = n - 1; i >= 0; i--) band += "L" + X(T[i]).toFixed(1) + "," + Y(D.us05[i]).toFixed(1);
    el("path", {d: band + "Z", fill: C.us, "fill-opacity": 0.13, stroke: "none"}, svg);
    [["un", 1.75], ["ea", 2], ["gl", 2], ["us", 2.25], ["actual", 2.75]].forEach(function (a) {
      var p = "";
      for (var j = 0; j < n; j++) p += (j ? "L" : "M") + X(T[j]).toFixed(1) + "," + Y(D[a[0]][j]).toFixed(1);
      el("path", {d: p, fill: "none", stroke: C[a[0]], "stroke-width": a[1], "stroke-linejoin": "round", "stroke-linecap": "round"}, svg);
    });
    var keys = ["actual", "us", "gl", "un", "ea"];
    var xe = X(T[n - 1]);
    keys.forEach(function (key) {
      el("circle", {cx: xe, cy: Y(D[key][n - 1]), r: 4, fill: C[key], stroke: "#fcfcfb", "stroke-width": 2}, svg);
    });
    if (!narrow) {
      var vals = keys.map(function (key) { return Y(D[key][n - 1]); });
      var neg = vals.map(function (v) { return -v; });
      var pos = spread(neg, 19, -(m.t + ph - 8)).map(function (v) { return -v; });
      keys.forEach(function (key, j) {
        var xl = xe + 16;
        el("path", {d: "M" + (xe + 5) + "," + vals[j] + "L" + (xe + 11) + "," + pos[j] + "L" + xl + "," + pos[j], fill: "none", stroke: "#c3c2b7", "stroke-width": 1}, svg);
        el("text", {x: xl + 4, y: pos[j] + 4, "class": "endlab" + (key === "actual" || key === "us" ? " strong" : "")}, svg).textContent = NAME[key] + "  " + fmt(D[key][n - 1]);
        if (key === "us") {
          el("text", {x: xl + 4, y: pos[j] + 19, "class": "endsub"}, svg).textContent = "5–95% of models: " + Math.round(D.us05[n - 1]) + " to " + Math.round(D.us95[n - 1]);
        }
      });
    }
    var cross = el("line", {y1: m.t, y2: m.t + ph, stroke: "#52514e", "stroke-width": 1, visibility: "hidden"}, svg);
    var dots = {};
    ["un", "ea", "gl", "us", "actual"].forEach(function (key) {
      dots[key] = el("circle", {r: 4.5, fill: C[key], stroke: "#fcfcfb", "stroke-width": 2, visibility: "hidden"}, svg);
    });
    var hit = el("rect", {x: m.l - 6, y: m.t, width: pw + 12, height: ph, fill: "transparent"}, svg);
    G = {X: X, Y: Y, m: m, pw: pw, ph: ph, cross: cross, dots: dots, W: W, svg: svg};
    hit.addEventListener("pointermove", function (e) {
      var r = svg.getBoundingClientRect();
      show(nearest((e.clientX - r.left) * (W / r.width)));
    });
    hit.addEventListener("pointerleave", function () { if (document.activeElement !== host) hide(); });
  }
  function nearest(px) {
    var best = 0, bd = Infinity;
    for (var i = 0; i < n; i++) {
      var dd = Math.abs(G.X(T[i]) - px);
      if (dd < bd) { bd = dd; best = i; }
    }
    return best;
  }
  function row(key, value, cls) {
    var sw = key ? '<span class="sw" style="background:' + C[key] + '"></span>' : "";
    return '<tr' + (cls ? ' class="' + cls + '"' : "") + "><td>" + sw + (key ? NAME[key] : value[0]) + '</td><td class="n">' + (key ? value : value[1]) + "</td></tr>";
  }
  function show(i) {
    if (!G) return;
    idx = i;
    var x = G.X(T[i]);
    G.cross.setAttribute("x1", x); G.cross.setAttribute("x2", x); G.cross.setAttribute("visibility", "visible");
    for (var key in G.dots) {
      G.dots[key].setAttribute("cx", x); G.dots[key].setAttribute("cy", G.Y(D[key][i]));
      G.dots[key].setAttribute("visibility", "visible");
    }
    var dt = new Date(T[i]);
    var head = DAYS[dt.getUTCDay()] + " " + dt.getUTCDate() + " " + MONTHS[dt.getUTCMonth()] + " " + dt.getUTCFullYear() + (i === 0 ? " (start)" : "");
    tip.innerHTML = '<div class="d">' + head + "</div><table>" +
      row("actual", fmt(D.actual[i])) + row("us", fmt(D.us[i])) +
      row(null, ["5–95% of models", Math.round(D.us05[i]) + " to " + Math.round(D.us95[i])], "sub") +
      row("gl", fmt(D.gl[i])) + row("ea", fmt(D.ea[i])) + row("un", fmt(D.un[i])) +
      '</table><div class="hint" style="margin-top:4px">bp since the close of 30 Dec 2025</div>';
    tip.style.display = "block";
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var left = x + 14 + tw > G.W ? x - 14 - tw : x + 14;
    var top = Math.max(4, Math.min(G.Y(D.actual[i]) - th / 2, G.m.t + G.ph - th));
    tip.style.left = Math.max(0, left) + "px";
    tip.style.top = top + "px";
  }
  function hide() {
    if (!G) return;
    G.cross.setAttribute("visibility", "hidden");
    for (var key in G.dots) G.dots[key].setAttribute("visibility", "hidden");
    tip.style.display = "none";
  }
  host.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft") { show(Math.max(0, idx - 1)); e.preventDefault(); }
    else if (e.key === "ArrowRight") { show(Math.min(n - 1, idx + 1)); e.preventDefault(); }
    else if (e.key === "Home") { show(0); e.preventDefault(); }
    else if (e.key === "End") { show(n - 1); e.preventDefault(); }
    else if (e.key === "Escape") { hide(); }
  });
  host.addEventListener("focus", function () { show(idx); });
  host.addEventListener("blur", hide);
  draw();
  if (window.ResizeObserver) new ResizeObserver(function () { draw(); }).observe(host);
  else window.addEventListener("resize", draw);
})();
</script>
</body>
</html>
"""
