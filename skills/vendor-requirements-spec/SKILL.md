---
name: vendor-requirements-spec
description: Write a vendor-ready requirement specification (for access points, switches, firewalls, servers, software or any tender/GeM purchase) with numbered MUST/SHOULD/INFO requirements, a test method for each, the lab evidence behind them, what the vendor must send, direct questions, and an Excel compliance sheet for vendors to fill. Use when the user wants to "tell the vendor what we need", "write requirements for the tender", "make a spec/RFP/compliance sheet", or compare vendor offers against requirements.
---

# vendor-requirements-spec

Pattern from a real campus Wi-Fi access-point tender spec (Oct 2026). A good spec is **testable**: every MUST has a test we will run on demo units. Every requirement traces back to a need or to our own lab evidence.

## 1. Gather inputs (ask only what is missing)
- **What is bought,** for which users and scale (for example 10,000 students × 3 devices).
- **Our own evidence:** lab tests (see `lab-experiment-log` notes), surveys, failures of current equipment. Each failure becomes a MUST with a "why".
- **Constraints:** budget model (capex, subscriptions), deadline, the systems it must work with (our RADIUS/LDAP), Indian procurement (GeM, certifications), support location.
- **Audience:** a vendor's pre-sales engineer, so use exact standards (RFC numbers, IEEE amendments, attribute names) and plain sentences.

## 2. Write the spec in Markdown (`template.md` next to this file)
- Sections: project summary → what our tests showed → requirement groups (A, B, C…) → what the vendor must send → questions to ask → out of scope.
- Requirement tables **must** use the header `| ID | Priority | Requirement | How we will test |`, so the compliance sheet script can read them.
- **Priorities:**
  - **MUST** means a "No" disqualifies the offer.
  - **SHOULD** means preferred and scored.
  - **INFO** means the vendor states a value.
  - Keep MUSTs to what we will really test; a MUST nobody tests is a wish.
- **Each requirement:** one testable behaviour, a standard reference where one exists, and a measurable target. Mark our own targets as ours, for example "(our target)".
- **Don't assert legal or certification duties you have not verified.** Ask the vendor to *state* compliance (for example "WPC ETA; state TEC MTCTE/BIS where applicable") and tell the user to confirm with the purchase office.
- **Ask for evidence, not adjectives:** a document and page, firmware version, demo units for N weeks, reference sites at similar scale, and a 5-year total cost including subscriptions.
- **Questions section:** the 10–15 questions that expose weak products. Ask exactly which device does X, on which port, after which event.

## 3. Build outputs
1. **Web page + PDF:** use the `report-publisher` skill (`build.py` turns MUST/SHOULD/INFO cells into pills, `to_pdf.py` makes the A4 PDF).
2. **Compliance sheet** for vendors:
   ```bash
   PY ~/.claude/skills/vendor-requirements-spec/scripts/compliance_sheet.py SPEC.md --out <Name>-Compliance-Sheet.csv
   ```
   It writes one row per requirement plus empty columns for: vendor answer, evidence, firmware, remarks, our test result and our notes. There are two outputs:
   - a **.xlsx**: navy header, frozen panes, filter, a Comply/Partly/No dropdown for the vendor, Pass/Fail/Not tested for us, and a "How to fill" sheet. It needs openpyxl, which is in the marker venv;
   - a **.csv** fallback, UTF-8 with a BOM so Excel opens it correctly. A Python without openpyxl produces only this one.

   `PY` is the `python` value in `~/.claude/setup.json` if that file exists, else `python3` (`py -3` on Windows; there, also set `PYTHONIOENCODING=utf-8`). For the .xlsx, `pip install openpyxl` (ask the user first).

   Check that the printed MUST/SHOULD counts match the spec, and fix any duplicate-ID warning.
3. Send the PDF and the .xlsx to the user. Remind them that the page is private until shared, and list the targets they should confirm.

## 4. Later: scoring offers
When offers arrive, read each filled sheet:
- Any MUST answered "No" disqualifies the offer.
- Treat "Partly" on a MUST as a "No" unless the evidence closes it.
- Score SHOULDs, then confirm the claims in the lab test before award.
