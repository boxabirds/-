import argparse
import os
import arxiv
import requests
import shutil
import datetime
from tqdm import tqdm
import time  # Import time module for throttling

# Constants
WAIT_TIME = 3  # seconds to wait between downloads to respect arXiv's rate limits

def download_paper(paper, destination):
    """Download the PDF of a single paper."""
    try:
        response = requests.get(paper.pdf_url, stream=True)
        with open(os.path.join(destination, f"{paper.get_short_id()}.pdf"), 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        return True
    except Exception as e:
        print(f"Error downloading {paper.get_short_id()}: {e}")
        return False

def fetch_and_download(subjects, days_back, destination):
    """Fetch papers from arXiv and download them."""
    client = arxiv.Client()
    if not os.path.exists(destination):
        os.makedirs(destination)

    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_back)
    search_query = " OR ".join([f"cat:{subject}" for subject in subjects])

    try:
        for paper in tqdm(client.results(arxiv.Search(query=search_query, sort_by=arxiv.SortCriterion.SubmittedDate)), desc="Downloading papers"):
            try:
                if paper.updated.replace(tzinfo=datetime.timezone.utc) >= cutoff_date:
                    pdf_path = os.path.join(destination, f"{paper.get_short_id()}.pdf")
                    if os.path.exists(pdf_path):
                        print("Skipping already downloaded paper: ", paper.title)
                    else:
                        if download_paper(paper, destination):
                            print(f"Downloaded: {paper.title}")
                            time.sleep(WAIT_TIME)  # Throttle requests to respect arXiv's rate limits
            except Exception as e:
                print(f"Error processing paper {paper.get_short_id()}: {e}")
                continue
    except arxiv.UnexpectedEmptyPageError as e:
        print(f"Encountered an empty page error, end of job")


def main(subjects, days_back, destination):
    fetch_and_download(subjects, days_back, destination)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download papers from arXiv based on subjects and date range.")
    parser.add_argument("--subjects", type=str, default="cs.CL,cs.AI", help="Comma-separated list of arXiv subjects.")
    parser.add_argument("--range", type=int, default=7, help="Number of days back to fetch papers.")
    parser.add_argument("--destination", type=str, help="Destination directory for PDFs.")
    
    args = parser.parse_args()
    subjects = args.subjects.split(',')
    days_back = args.range
    destination_dir = args.destination if args.destination else '-'.join(subjects).replace('.', '_')

    main(subjects, days_back, destination_dir)
