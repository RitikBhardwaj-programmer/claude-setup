"""Make a vendor compliance sheet (CSV that opens in Excel) from a requirements Markdown file.

Usage (stdlib only):
  python3 compliance_sheet.py SPEC.md [--out sheet.csv]     (stdlib; with openpyxl it also writes .xlsx)

Reads every Markdown table whose header has "ID" and "Priority" columns (the spec format of this
skill), and writes one row per requirement with empty vendor-answer columns. The CSV is UTF-8 with
a BOM so Excel shows the characters correctly. Prints counts per priority so they can be checked
against the spec.
"""
import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

VENDOR_COLS = ["Vendor answer (Comply / Partly / No)", "Evidence (document + page)",
               "Model / firmware tested", "Vendor remarks", "Our test result", "Our notes"]


def strip_md(cell):
    cell = re.sub(r"\*\*(.+?)\*\*", r"\1", cell)
    cell = re.sub(r"`([^`]*)`", r"\1", cell)
    cell = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cell)
    return cell.replace("\\|", "|").strip()


def split_row(line):
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [strip_md(c) for c in cells]


def write_xlsx(rows, path, title):
    """Formatted Excel sheet with dropdowns; returns the path, or None if openpyxl is missing."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        return None
    wb = Workbook()
    ws = wb.active
    ws.title = "Compliance"
    head = ["Section", "ID", "Priority", "Requirement", "How we will test"] + VENDOR_COLS
    ws.append(head)
    for r in rows:
        ws.append([r["Section"], r["ID"], r["Priority"], r["Requirement"], r["How we will test"]] + [""] * len(VENDOR_COLS))
    navy, must_fill, vendor_fill = "1F3A5F", PatternFill("solid", fgColor="EEF2F7"), PatternFill("solid", fgColor="FFF8E1")
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=navy)
        c.alignment = Alignment(wrap_text=True, vertical="center")
    widths = [26, 6, 9, 60, 42, 18, 26, 18, 28, 16, 24]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        if row[2].value == "MUST":
            row[2].fill = must_fill
            row[2].font = Font(bold=True, color=navy)
        for c in row[5:9]:
            c.fill = vendor_fill
    n = len(rows) + 1
    vendor = DataValidation(type="list", formula1='"Comply,Partly,No"', allow_blank=True)
    ours = DataValidation(type="list", formula1='"Pass,Fail,Not tested"', allow_blank=True)
    ws.add_data_validation(vendor)
    ws.add_data_validation(ours)
    vendor.add(f"F2:F{n}")
    ours.add(f"J2:J{n}")
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{ws.cell(1, len(head)).column_letter}{n}"
    info = wb.create_sheet("How to fill")
    for line in [f"Compliance sheet for: {title}",
                 "Answer every row in the yellow columns.",
                 "Vendor answer: Comply / Partly / No (dropdown). A 'No' on any MUST disqualifies the offer.",
                 "Evidence: document name and page that proves the answer.",
                 "Model / firmware: the exact model and firmware version the answer applies to.",
                 "The last two columns are filled by us after the lab test."]:
        info.append([line])
    info.column_dimensions["A"].width = 100
    wb.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    spec = Path(a.spec)
    out = Path(a.out) if a.out else spec.with_name(spec.stem + "-compliance-sheet.csv")
    lines = spec.read_text(encoding="utf-8").splitlines()

    section, header, rows = "", None, []
    for ln in lines:
        if ln.startswith("## "):
            section, header = ln[3:].strip(), None
            continue
        if not ln.lstrip().startswith("|"):
            header = None
            continue
        cells = split_row(ln)
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if "id" not in header or "priority" not in header:
            continue
        rec = dict(zip(header, cells))
        rows.append({"Section": section, "ID": rec.get("id", ""), "Priority": rec.get("priority", ""),
                     "Requirement": rec.get("requirement", ""),
                     "How we will test": rec.get("how we will test", rec.get("test", ""))})
    if not rows:
        sys.exit("No requirement tables found (need header columns 'ID' and 'Priority').")

    ids = Counter(r["ID"] for r in rows)
    dupes = [i for i, n in ids.items() if n > 1]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Section", "ID", "Priority", "Requirement", "How we will test"] + VENDOR_COLS)
        for r in rows:
            w.writerow([r["Section"], r["ID"], r["Priority"], r["Requirement"], r["How we will test"]] + [""] * len(VENDOR_COLS))
    counts = Counter(r["Priority"] for r in rows)
    print(f"wrote {out} ({len(rows)} requirements: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ")")
    xlsx = write_xlsx(rows, out.with_suffix(".xlsx"), spec.stem)
    print(f"wrote {xlsx}" if xlsx else "openpyxl not available: CSV only (run with the marker venv Python for .xlsx)")
    if dupes:
        print("WARNING duplicate IDs:", ", ".join(dupes))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
