"""Utility functions for SEO Automation"""

import logging
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# Setup logging
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            LOG_DIR / f"seo_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger(__name__)


def fetch_sitemap_urls(sitemap_url, recursive=True):
    """Fetch all URLs from a sitemap (including sitemap indexes)"""

    urls = []

    try:
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.content)

        # Handle namespace
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        # Check if sitemap index
        sitemaps = root.findall('.//sm:sitemap/sm:loc', ns)

        if sitemaps and recursive:
            # This is a sitemap index
            for sitemap in sitemaps:
                sub_urls = fetch_sitemap_urls(sitemap.text, recursive=True)
                urls.extend(sub_urls)
        else:
            # Regular sitemap
            for url_elem in root.findall('.//sm:url', ns):
                loc = url_elem.find('sm:loc', ns)
                lastmod = url_elem.find('sm:lastmod', ns)

                if loc is not None:
                    url_data = {
                        'url': loc.text,
                        'lastmod': lastmod.text if lastmod is not None else None
                    }
                    urls.append(url_data)

        logger.info(f"Fetched {len(urls)} URLs from {sitemap_url}")

    except Exception as e:
        logger.error(f"Error fetching sitemap {sitemap_url}: {e}")

    return urls


def chunk_list(lst, chunk_size):
    """Split a list into chunks of specified size"""

    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def save_json(data, filepath):
    """Save data to JSON file"""

    import json

    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved data to {filepath}")


def load_json(filepath, default=None):
    """Load data from JSON file"""

    import json

    filepath = Path(filepath)

    if not filepath.exists():
        return default if default is not None else {}

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
