import argparse
from pathlib import Path
import arxiv
from tqdm import tqdm
import time  # Import time module for throttling
import datetime
import re

# Constants
WAIT_TIME = 3  # seconds to wait between downloads to respect arXiv's rate limits
MAX_TITLE_LENGTH = 200  # Maximum length of the title in the filename to avoid too long filenames

def filename_friendly_title(title):
    """Sanitize the paper title to make it filename-friendly."""
    sanitized = re.sub(r'[\\/*?:"<>|]', '', title)  # Remove invalid filename characters
    #sanitized = sanitized.replace(' ', '_')  # Replace spaces with underscores
    return sanitized[:MAX_TITLE_LENGTH]  # Truncate title to avoid too long filenames

def download_paper(paper, pdf_output_path:Path, source_output_path:Path=None):
    """Download the PDF and optionally the source of a single paper if they don't already exist."""
    filename_stem = f"{paper.get_short_id()} {filename_friendly_title(paper.title)}"
    
    # Check and Download PDF
    pdf_file_path = pdf_output_path / f"{filename_stem}.pdf"
    if not pdf_file_path.exists():
        try:
            paper.download_pdf(dirpath=str(pdf_output_path), filename=pdf_file_path.name)
            print(f"Downloaded PDF: {pdf_file_path.name}")
            time.sleep(WAIT_TIME)  # Throttle requests to respect arXiv's rate limits only when we've actually downloaded
        except Exception as e:
            print(f"Error downloading PDF {paper.get_short_id()}: {e}")
    else:
        print(f"PDF already exists, skipping: {pdf_file_path.name}")
    
    # Check and Download source if requested
    if source_output_path is not None:
        source_file_path = source_output / f"{filename_stem}.tar.gz"
        if not source_file_path.exists():
            try:
                paper.download_source(dirpath=str(source_output), filename=source_file_path.name)
                print(f"Downloaded source: {source_file_path.name}")
                
            except Exception as e:
                print(f"Error downloading source {paper.get_short_id()}: {e}")
        else:
            print(f"Source file already exists, skipping: {source_file_path.name}")
    
    

def fetch_and_download(subjects, days_back, pdf_output, include_source, source_output):
    """Fetch papers from arXiv and download them."""
    client = arxiv.Client()

    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_back)
    
    # Exclude withdrawn papers
    exclusion_terms = ' AND NOT (ti:"withdrawn" OR abs:"withdrawn" OR comm:"withdrawn")'
    search_query = " OR ".join([f"cat:{subject}" for subject in subjects]) + exclusion_terms

    pdf_output_path = Path(pdf_output)
    pdf_output_path.mkdir(parents=True, exist_ok=True)

    if include_source:
        source_output_path = Path(source_output)
        source_output_path.mkdir(parents=True, exist_ok=True)

    try:
        for paper in tqdm(client.results(arxiv.Search(query=search_query, sort_by=arxiv.SortCriterion.SubmittedDate)), desc="Downloading papers"):
            if paper.updated.replace(tzinfo=datetime.timezone.utc) >= cutoff_date:
                download_paper(paper, pdf_output_path, source_output_path)
    except arxiv.UnexpectedEmptyPageError as e:
        print(f"Encountered an empty page error, end of job")

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download papers from arXiv based on subjects and date range.")
    parser.add_argument("--subjects", type=str, default="cs.CL,cs.AI", help="Comma-separated list of arXiv subjects.")
    parser.add_argument("--range", type=int, default=7, help="Number of days back to fetch papers.")
    parser.add_argument("--pdf-output", type=str, default="output/pdf", help="Output directory for PDFs.")
    parser.add_argument("--include-source", action="store_true", default=True, help="Download source files (LaTeX and images) if they exist.")
    parser.add_argument("--source-output", type=str, default="output/source", help="Output directory for source files.")
    
    args = parser.parse_args()
    subjects = args.subjects.split(',')
    days_back = args.range
    pdf_output = Path(args.pdf_output).resolve()
    include_source = args.include_source
    source_output = Path(args.source_output).resolve()

    if include_source:
        if not source_output.exists():
            source_output.mkdir(parents=True, exist_ok=True)

    fetch_and_download(subjects, days_back, pdf_output, include_source, source_output)