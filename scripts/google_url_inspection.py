#!/usr/bin/env python3
"""
Google URL Inspection API
Request indexing for specific URLs
"""

import sys
import json
import time
from pathlib import Path
from config import load_sites
from google_auth import get_search_console_service
from utils import logger, fetch_sitemap_urls, chunk_list, save_json

# Google has strict rate limits
MAX_REQUESTS_PER_DAY = 2000  # Per project
MAX_REQUESTS_PER_MINUTE = 600  # Per project
BATCH_SIZE = 10  # Our conservative batch size

DATA_DIR = Path(__file__).parent.parent / 'data'


def inspect_url(service, inspection_url, site_url):
    """Inspect a single URL"""

    try:
        request_body = {
            'inspectionUrl': inspection_url,
            'siteUrl': site_url
        }

        request = service.urlInspection().index().inspect(body=request_body)
        response = request.execute()

        inspection_result = response.get('inspectionResult', {})
        index_status = inspection_result.get('indexStatusResult', {})

        verdict = index_status.get('verdict', 'UNKNOWN')
        coverage_state = index_status.get('coverageState')
        crawled_as = index_status.get('crawledAs')
        last_crawl_time = index_status.get('lastCrawlTime')

        logger.info(f"[INSPECT] {inspection_url}: {verdict} ({coverage_state})")

        return {
            'url': inspection_url,
            'verdict': verdict,
            'coverage_state': coverage_state,
            'crawled_as': crawled_as,
            'last_crawl_time': last_crawl_time,
            'indexed': verdict == 'PASS'
        }

    except Exception as e:
        logger.error(f"[ERROR] Error inspecting {inspection_url}: {e}")
        return None


def request_indexing(service, inspection_url, site_url):
    """Request indexing for a URL"""

    try:
        # First inspect
        inspection = inspect_url(service, inspection_url, site_url)

        if not inspection:
            return False

        # If already indexed, skip
        if inspection['indexed']:
            logger.info(f"[OK] Already indexed: {inspection_url}")
            return True

        # Request indexing (API removed - use sitemap instead)
        logger.warning(f"[WARN] URL not indexed, will be picked up via sitemap: {inspection_url}")

        return False

    except Exception as e:
        logger.error(f"[ERROR] Error requesting indexing for {inspection_url}: {e}")
        return False


def bulk_inspect(site, max_urls=100):
    """Bulk inspect URLs for a site"""

    logger.info(f"[PROCESSING] Bulk inspecting: {site['name']}")

    service = get_search_console_service()
    site_url = site['google_property']

    # Fetch all URLs from sitemap
    sitemap_urls = fetch_sitemap_urls(site['sitemap'])

    if not sitemap_urls:
        logger.warning(f"[WARN] No URLs found in sitemap")
        return []

    urls_to_check = [u['url'] for u in sitemap_urls]

    # Limit to avoid rate limits (check only top pages)
    urls_to_check = urls_to_check[:max_urls]

    logger.info(f"[INSPECT] Inspecting {len(urls_to_check)} URLs")

    results = []
    indexed_urls = []
    not_indexed_urls = []

    for i, url in enumerate(urls_to_check, 1):
        result = inspect_url(service, url, site_url)

        if result:
            results.append(result)
            if result['indexed']:
                indexed_urls.append(url)
            else:
                not_indexed_urls.append(url)

        # Rate limiting
        if i % 10 == 0:
            logger.info(f"Progress: {i}/{len(urls_to_check)}")
            time.sleep(10)  # 10 seconds per 10 requests
        else:
            time.sleep(1)

    # Statistics
    total = len(results)
    indexed = len(indexed_urls)
    not_indexed = total - indexed

    logger.info("=" * 60)
    logger.info(f"[STATS] Results for {site['name']}:")
    logger.info(f"   Total checked: {total}")
    logger.info(f"   Indexed: {indexed} ({indexed/total*100:.1f}%)" if total > 0 else "   Indexed: 0")
    logger.info(f"   Not indexed: {not_indexed}")
    logger.info("=" * 60)

    return results


def save_inspection_results(site, results):
    """Save inspection results to JSON file"""

    indexed = [r for r in results if r['indexed']]
    not_indexed = [r for r in results if not r['indexed']]

    # Save all results
    output_file = DATA_DIR / f"inspection_{site['domain']}.json"
    save_json(results, output_file)

    # Save indexed URLs separately
    indexed_file = DATA_DIR / 'google_indexed_urls.json'
    indexed_data = {}
    if indexed_file.exists():
        with open(indexed_file, 'r') as f:
            indexed_data = json.load(f)

    indexed_data[site['domain']] = [r['url'] for r in indexed]
    save_json(indexed_data, indexed_file)

    # Save pending URLs (not indexed)
    pending_file = DATA_DIR / 'google_pending_urls.json'
    pending_data = {}
    if pending_file.exists():
        with open(pending_file, 'r') as f:
            pending_data = json.load(f)

    pending_data[site['domain']] = [r['url'] for r in not_indexed]
    save_json(pending_data, pending_file)


def main():
    """Main function"""

    mode = sys.argv[1] if len(sys.argv) > 1 else 'inspect'
    max_urls = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    logger.info(f"[START] Starting URL Inspection (mode: {mode}, max_urls: {max_urls})")
    logger.info("=" * 60)

    sites = load_sites()

    for site in sites:
        if not site['enabled']:
            logger.info(f"[SKIP] Skipping disabled site: {site['name']}")
            continue

        if mode == 'inspect':
            results = bulk_inspect(site, max_urls=max_urls)

            if results:
                save_inspection_results(site, results)
                logger.info(f"[SAVED] Results saved for {site['domain']}")

        # Wait between sites
        time.sleep(5)

    logger.info("[DONE] URL Inspection completed!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
