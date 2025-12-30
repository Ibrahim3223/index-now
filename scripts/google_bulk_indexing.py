#!/usr/bin/env python3
"""
Google Bulk Indexing Strategy
Combined approach using multiple techniques
"""

import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from config import load_sites
from google_auth import get_search_console_service
from utils import logger, fetch_sitemap_urls

DATA_DIR = Path(__file__).parent.parent / 'data'


def ping_google(sitemap_url):
    """Ping Google to crawl sitemap"""

    ping_url = f"https://www.google.com/ping?sitemap={sitemap_url}"

    try:
        response = requests.get(ping_url, timeout=10)
        if response.status_code == 200:
            logger.info(f"[OK] Pinged Google for: {sitemap_url}")
            return True
    except Exception as e:
        logger.error(f"[ERROR] Ping failed: {e}")

    return False


def ping_services(url):
    """Ping multiple indexing services"""

    services = [
        f"https://www.google.com/ping?sitemap={url}",
        f"https://www.bing.com/ping?sitemap={url}",
    ]

    results = []

    for service in services:
        try:
            response = requests.get(service, timeout=10)
            success = response.status_code == 200
            results.append({'service': service, 'success': success})
            logger.info(f"{'[OK]' if success else '[FAIL]'} {service}")
        except Exception as e:
            results.append({'service': service, 'success': False})
            logger.warning(f"[WARN] {service}: {e}")

        time.sleep(1)

    return results


def create_rss_feed(site, urls, limit=50):
    """Create RSS feed for latest content"""

    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')

    SubElement(channel, 'title').text = site['name']
    SubElement(channel, 'link').text = f"https://{site['domain']}"
    SubElement(channel, 'description').text = f"Latest content from {site['name']}"
    SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Add latest URLs
    for url_data in urls[:limit]:
        item = SubElement(channel, 'item')

        # Extract title from URL
        url_path = url_data['url'].rstrip('/').split('/')[-1]
        title = url_path.replace('-', ' ').title() if url_path else site['name']

        SubElement(item, 'title').text = title
        SubElement(item, 'link').text = url_data['url']
        SubElement(item, 'guid').text = url_data['url']

        if url_data.get('lastmod'):
            SubElement(item, 'pubDate').text = url_data['lastmod']
        else:
            SubElement(item, 'pubDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Pretty print
    xml_str = minidom.parseString(tostring(rss)).toprettyxml(indent="  ")

    # Save RSS
    rss_file = DATA_DIR / f"rss_{site['domain']}.xml"
    with open(rss_file, 'w', encoding='utf-8') as f:
        f.write(xml_str)

    logger.info(f"[RSS] RSS feed created: {rss_file}")

    return str(rss_file)


def submit_to_archives(domain):
    """Submit to web archives"""

    archive_urls = [
        f"https://web.archive.org/save/https://{domain}",
    ]

    results = []

    for archive_url in archive_urls:
        try:
            response = requests.get(archive_url, timeout=30)
            success = response.status_code in [200, 302]
            results.append({'archive': archive_url, 'success': success})
            logger.info(f"{'[OK]' if success else '[WARN]'} Archived: {archive_url}")
        except Exception as e:
            results.append({'archive': archive_url, 'success': False})
            logger.warning(f"[WARN] Archive failed: {archive_url} - {e}")

        time.sleep(2)

    return results


def aggressive_indexing_strategy(site):
    """Multi-pronged indexing approach"""

    logger.info(f"[TARGET] Aggressive indexing for: {site['name']}")
    logger.info("=" * 60)

    sitemap_url = site['sitemap']
    domain = site['domain']

    results = {
        'site': site['name'],
        'domain': domain,
        'timestamp': datetime.now().isoformat(),
        'steps': []
    }

    # 1. Ping Google
    logger.info("[1/5] Pinging Google...")
    google_ping = ping_google(sitemap_url)
    results['steps'].append({'step': 'ping_google', 'success': google_ping})

    # 2. Ping multiple services
    logger.info("[2/5] Pinging indexing services...")
    service_pings = ping_services(sitemap_url)
    results['steps'].append({'step': 'ping_services', 'results': service_pings})

    # 3. Submit to Search Console
    logger.info("[3/5] Submitting to Google Search Console...")
    try:
        service = get_search_console_service()
        service.sitemaps().submit(
            siteUrl=site['google_property'],
            feedpath=sitemap_url
        ).execute()
        logger.info("[OK] Submitted to GSC")
        results['steps'].append({'step': 'gsc_submit', 'success': True})
    except Exception as e:
        logger.error(f"[ERROR] GSC submission failed: {e}")
        results['steps'].append({'step': 'gsc_submit', 'success': False, 'error': str(e)})

    # 4. Create and save RSS feed
    logger.info("[4/5] Creating RSS feed...")
    urls = fetch_sitemap_urls(sitemap_url)
    if urls:
        rss_file = create_rss_feed(site, urls)
        results['steps'].append({'step': 'rss_feed', 'success': True, 'file': rss_file})
    else:
        results['steps'].append({'step': 'rss_feed', 'success': False, 'error': 'No URLs found'})

    # 5. Submit to web archives
    logger.info("[5/5] Submitting to web archives...")
    archive_results = submit_to_archives(domain)
    results['steps'].append({'step': 'web_archives', 'results': archive_results})

    logger.info(f"[DONE] Aggressive indexing completed for {site['name']}")
    logger.info("=" * 60)

    return results


def main():
    """Main function"""

    logger.info("[START] Starting Bulk Indexing Strategy")
    logger.info("=" * 60)

    sites = load_sites()

    all_results = []

    for site in sites:
        if not site['enabled']:
            logger.info(f"[SKIP] Skipping disabled site: {site['name']}")
            continue

        result = aggressive_indexing_strategy(site)
        all_results.append(result)

        # Wait between sites
        time.sleep(5)

    # Save results
    output_file = DATA_DIR / f"bulk_indexing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    logger.info(f"[SAVED] Results saved: {output_file}")
    logger.info("[DONE] Bulk indexing completed!")

    return 0


if __name__ == '__main__':
    sys.exit(main())
