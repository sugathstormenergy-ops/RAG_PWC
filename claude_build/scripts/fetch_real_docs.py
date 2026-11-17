#!/usr/bin/env python3
"""
Download the REAL public engineering documents into data/real/.

Why this script exists: the sandbox this project was first built in has no
general internet access (only a locked-down package-manager allowlist), so
the real public PDFs below could not be downloaded there. Run this script on
your own machine (normal internet access, Wi-Fi on) before you switch Wi-Fi
off to demonstrate the tool offline, per Task 7.

Usage:
    python scripts/fetch_real_docs.py

It is safe to re-run: existing files are skipped.
"""
import os
import sys
import urllib.request

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "real")
os.makedirs(OUT_DIR, exist_ok=True)

# (filename, url, notes)
# NOTE: government/standards sites occasionally move files. If a URL 404s,
# search for the document name per the assignment's "Useful links" page --
# ASSIST Quick Search (quicksearch.dla.mil) for MIL-STDs, ntrs.nasa.gov for
# NASA reports, faa.gov for Advisory Circulars, drdo.gov.in for DSJ papers,
# archive.org for scanned "technical manual TM 9" manuals.
DOCUMENTS = [
    (
        "NASA-SP-2016-6105-Rev2-SE-Handbook.pdf",
        "https://www.nasa.gov/sites/default/files/atoms/files/nasa_systems_engineering_handbook_0.pdf",
        "NASA Systems Engineering Handbook (requirement/verification terms).",
    ),
    (
        "NASA-SP-2016-6105-SUPPL-Expanded-Guidance.pdf",
        "https://ntrs.nasa.gov/api/citations/20170007239/downloads/20170007239.pdf",
        "NASA SE Handbook companion: Expanded Guidance for NASA Systems Engineering.",
    ),
    # The three MIL-STDs below are distributed via ASSIST Quick Search
    # (quicksearch.dla.mil) or mirrored on everyspec.com; download the
    # "Distribution A" (public release) copy and drop it in data/real/ with
    # one of the file names below. Automated download is intentionally not
    # attempted here because document IDs / redirect URLs on ASSIST change
    # and the site expects interactive navigation.
    # "MIL-STD-810H.pdf"   <- environmental engineering considerations/tests
    # "MIL-STD-882E.pdf"   <- system safety
    # "MIL-STD-461G.pdf"   <- EMI requirements/control
    # "FAA-AC-xx-xx.pdf"   <- 2-3 short FAA Advisory Circulars from faa.gov
    # "DSJ-paper-1.pdf"    <- 1-2 Defence Science Journal (DRDO) open papers
    # "TM9-scanned.pdf"    <- 1-2 scanned "technical manual TM 9" from
    #                         archive.org (good OCR test case)
]

MANUAL_SOURCES = """
Manual downloads needed (interactive sites that resist scripted downloads):

1. MIL-STD-810H, MIL-STD-882E, MIL-STD-461G
   -> https://quicksearch.dla.mil/qsSearch.aspx  (search by document number,
      take only "Distribution A" / public-release copies)
   -> mirror: https://www.everyspec.com/MIL-STD/

2. 2-3 NASA test reports / design reviews
   -> https://ntrs.nasa.gov  (search "test report" or "design review")

3. 2-3 FAA Advisory Circulars
   -> https://www.faa.gov/regulations_policies/advisory_circulars

4. 1-2 Defence Science Journal (DRDO) open-access papers
   -> https://publications.drdo.gov.in/ojs/index.php/dsj

5. 1-2 scanned military technical manuals (OCR test)
   -> https://archive.org  (search "technical manual TM 9")

Save each as a PDF into data/real/, then re-run:
    python src/ingest.py --rebuild
to add them to the index.
"""


def download(filename, url):
    dest = os.path.join(OUT_DIR, filename)
    if os.path.exists(dest):
        print(f"[skip] {filename} already present")
        return
    print(f"[get ] {filename} <- {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as fh:
            fh.write(resp.read())
        print(f"[ ok ] {filename}")
    except Exception as e:
        print(f"[FAIL] {filename}: {e}", file=sys.stderr)


if __name__ == "__main__":
    for filename, url, _notes in DOCUMENTS:
        download(filename, url)
    print(MANUAL_SOURCES)
