#!/usr/bin/env python3
"""
Google Search Console - Sitemap Submission
Submits sitemaps to Google Search Console for all sites
"""

import sys
import time
from config import load_sites
from google_auth import get_search_console_service
from utils import logger


def submit_sitemap(service, site_url, sitemap_url):
    """Submit sitemap to Google Search Console"""

    try:
        request = service.sitemaps().submit(
            siteUrl=site_url,
            feedpath=sitemap_url
        )

        response = request.execute()
        logger.info(f"[OK] Sitemap submitted: {sitemap_url}")
        return True

    except Exception as e:
        logger.error(f"[ERROR] Error submitting sitemap {sitemap_url}: {e}")
        return False


def get_sitemap_status(service, site_url, sitemap_url):
    """Get sitemap status from GSC"""

    try:
        request = service.sitemaps().get(
            siteUrl=site_url,
            feedpath=sitemap_url
        )

        response = request.execute()

        status = {
            'path': response.get('path'),
            'lastSubmitted': response.get('lastSubmitted'),
            'lastDownloaded': response.get('lastDownloaded'),
            'isPending': response.get('isPending'),
            'isSitemapsIndex': response.get('isSitemapsIndex'),
            'errors': response.get('errors', 0),
            'warnings': response.get('warnings', 0)
        }

        logger.info(f"[STATUS] Sitemap status: {status}")
        return status

    except Exception as e:
        logger.warning(f"[WARN] Could not get sitemap status: {e}")
        return None


def list_sitemaps(service, site_url):
    """List all sitemaps for a site"""

    try:
        request = service.sitemaps().list(siteUrl=site_url)
        response = request.execute()

        sitemaps = response.get('sitemap', [])
        logger.info(f"[LIST] Found {len(sitemaps)} sitemaps for {site_url}")

        for sm in sitemaps:
            logger.info(f"  - {sm.get('path')}")

        return sitemaps

    except Exception as e:
        logger.error(f"[ERROR] Error listing sitemaps: {e}")
        return []


def main():
    """Main function"""

    logger.info("[START] Starting Google Sitemap Submission")
    logger.info("=" * 60)

    # Get Search Console service
    service = get_search_console_service()

    # Load sites
    sites = load_sites()

    results = []

    for site in sites:
        if not site['enabled']:
            logger.info(f"[SKIP] Skipping disabled site: {site['name']}")
            continue

        logger.info(f"[PROCESSING] {site['name']}")

        site_url = site['google_property']
        sitemap_url = site['sitemap']

        # Check current status
        status = get_sitemap_status(service, site_url, sitemap_url)

        # Submit sitemap
        success = submit_sitemap(service, site_url, sitemap_url)

        results.append({
            'site': site['name'],
            'success': success,
            'status': status
        })

        # Rate limiting
        time.sleep(2)

    # Summary
    logger.info("=" * 60)
    logger.info("[SUMMARY] SITEMAP SUBMISSION SUMMARY")
    logger.info("=" * 60)

    success_count = 0
    fail_count = 0

    for result in results:
        status = "[OK]" if result['success'] else "[FAIL]"
        logger.info(f"{status} {result['site']}")
        if result['success']:
            success_count += 1
        else:
            fail_count += 1

    logger.info("=" * 60)
    logger.info(f"Total: {len(results)} | Success: {success_count} | Failed: {fail_count}")

    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
