import argparse
import os
import arxiv
import requests
import shutil
import datetime
from tqdm import tqdm

def download_paper(paper, destination):
    """Download the PDF of a single paper."""
    response = requests.get(paper.pdf_url, stream=True)
    with open(os.path.join(destination, f"{paper.get_short_id()}.pdf"), 'wb') as f:
        shutil.copyfileobj(response.raw, f)

def fetch_and_download(subjects, days_back, destination):
    """Fetch papers from arXiv and download them."""
    # Initialize arXiv client
    client = arxiv.Client()

    # Ensure the destination directory exists
    if not os.path.exists(destination):
        os.makedirs(destination)

    # Convert days_back to a datetime for comparison
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_back)

    # Fetch and download papers
    search_query = " OR ".join([f"cat:{subject}" for subject in subjects])
    for paper in tqdm(client.results(arxiv.Search(query=search_query, sort_by=arxiv.SortCriterion.SubmittedDate)), desc="Downloading papers"):
        if paper.updated.replace(tzinfo=datetime.timezone.utc) >= cutoff_date:
            pdf_path = os.path.join(destination, f"{paper.get_short_id()}.pdf")
            if not os.path.exists(pdf_path):
                download_paper(paper, destination)
                print(f"Downloaded: {paper.title}")

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
