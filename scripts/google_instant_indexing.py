#!/usr/bin/env python3
"""
Google Instant Indexing API
Submit URLs directly to Google for faster indexing
Each site uses its own Google Cloud project (200 URLs/day per project)
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import load_sites
from utils import logger, fetch_sitemap_urls, save_json, load_json

# Constants
DAILY_LIMIT = 200  # Google's daily limit per project
RESUBMIT_AFTER_DAYS = 30  # Re-submit URLs older than this

# Directories
DATA_DIR = Path(__file__).parent.parent / 'data'
CREDENTIALS_DIR = Path(__file__).parent.parent / 'credentials'

# Progress file
PROGRESS_FILE = DATA_DIR / 'indexing_progress.json'
HISTORY_FILE = DATA_DIR / 'indexing_history.json'

# Indexing API scope
INDEXING_SCOPES = ['https://www.googleapis.com/auth/indexing']


def get_indexing_service(credential_file):
    """Get authenticated Indexing API service for a specific site"""

    if not credential_file.exists():
        raise FileNotFoundError(f"Credential file not found: {credential_file}")

    credentials = service_account.Credentials.from_service_account_file(
        str(credential_file),
        scopes=INDEXING_SCOPES
    )

    service = build('indexing', 'v3', credentials=credentials)
    return service


def get_site_credential_file(site):
    """Get the credential file path for a site"""

    # Check for site-specific credential file
    credential_filename = site.get('indexing_credential')

    if not credential_filename:
        logger.warning(f"[WARN] No indexing_credential defined for {site['name']}")
        return None

    credential_path = CREDENTIALS_DIR / credential_filename

    if not credential_path.exists():
        logger.warning(f"[WARN] Credential file not found: {credential_path}")
        return None

    return credential_path


def load_progress():
    """Load indexing progress from file"""
    return load_json(PROGRESS_FILE, default={})


def save_progress(progress):
    """Save indexing progress to file"""
    save_json(progress, PROGRESS_FILE)


def load_history():
    """Load indexing history from file"""
    return load_json(HISTORY_FILE, default={})


def save_history(history):
    """Save indexing history to file"""
    save_json(history, HISTORY_FILE)


def get_site_progress(progress, domain):
    """Get or initialize progress for a site"""

    if domain not in progress:
        progress[domain] = {
            'last_index': 0,
            'total_urls': 0,
            'last_run': None,
            'daily_sent': 0,
            'daily_reset_date': None,
            'completed_first_pass': False
        }

    # Reset daily counter if it's a new day
    today = datetime.now().strftime('%Y-%m-%d')
    if progress[domain].get('daily_reset_date') != today:
        progress[domain]['daily_sent'] = 0
        progress[domain]['daily_reset_date'] = today

    return progress[domain]


def submit_url_to_indexing(service, url, action='URL_UPDATED'):
    """Submit a single URL to Google Indexing API"""

    try:
        body = {
            'url': url,
            'type': action  # URL_UPDATED or URL_DELETED
        }

        response = service.urlNotifications().publish(body=body).execute()

        logger.info(f"[OK] Submitted: {url}")
        return True, response

    except Exception as e:
        error_msg = str(e)

        # Check for quota exceeded
        if 'quota' in error_msg.lower() or '429' in error_msg:
            logger.warning(f"[QUOTA] Daily limit reached")
            return False, 'QUOTA_EXCEEDED'

        logger.error(f"[ERROR] Failed to submit {url}: {e}")
        return False, error_msg


def get_urls_to_submit(site, progress, history):
    """Determine which URLs to submit based on progress and history"""

    domain = site['domain']
    site_progress = get_site_progress(progress, domain)
    site_history = history.get(domain, {})

    # Fetch all URLs from sitemap
    sitemap_urls = fetch_sitemap_urls(site['sitemap'])

    if not sitemap_urls:
        logger.warning(f"[WARN] No URLs found in sitemap for {domain}")
        return []

    total_urls = len(sitemap_urls)
    site_progress['total_urls'] = total_urls

    urls_to_submit = []
    now = datetime.now()

    # If first pass not completed, continue from last index
    if not site_progress.get('completed_first_pass', False):
        last_index = site_progress.get('last_index', 0)

        if last_index < total_urls:
            # Continue from where we left off
            remaining = sitemap_urls[last_index:]
            urls_to_submit = [u['url'] for u in remaining]
            logger.info(f"[CONTINUE] Resuming from index {last_index}/{total_urls}")
        else:
            # First pass completed
            site_progress['completed_first_pass'] = True
            site_progress['last_index'] = 0
            logger.info(f"[COMPLETE] First pass completed for {domain}")

    # If first pass completed, look for URLs to re-submit
    if site_progress.get('completed_first_pass', False):
        logger.info(f"[RECHECK] Looking for URLs to re-submit...")

        for url_data in sitemap_urls:
            url = url_data['url']
            lastmod = url_data.get('lastmod')

            # Get last submission info
            last_submitted = site_history.get(url, {}).get('last_submitted')
            last_lastmod = site_history.get(url, {}).get('lastmod')

            should_resubmit = False
            reason = None

            # Check if lastmod changed
            if lastmod and last_lastmod and lastmod != last_lastmod:
                should_resubmit = True
                reason = 'lastmod_changed'

            # Check if 30 days passed since last submission
            if last_submitted:
                last_date = datetime.fromisoformat(last_submitted)
                days_passed = (now - last_date).days

                if days_passed >= RESUBMIT_AFTER_DAYS:
                    should_resubmit = True
                    reason = f'{days_passed}_days_old'

            # If never submitted, always submit
            if not last_submitted:
                should_resubmit = True
                reason = 'never_submitted'

            if should_resubmit:
                urls_to_submit.append(url)

        logger.info(f"[RECHECK] Found {len(urls_to_submit)} URLs to re-submit")

    return urls_to_submit


def process_site(site, progress, history):
    """Process a single site for instant indexing"""

    domain = site['domain']
    logger.info(f"[SITE] Processing: {site['name']} ({domain})")
    logger.info("=" * 60)

    # Get credential file
    credential_file = get_site_credential_file(site)
    if not credential_file:
        logger.error(f"[SKIP] No valid credential for {domain}")
        return 0

    # Get indexing service
    try:
        service = get_indexing_service(credential_file)
    except Exception as e:
        logger.error(f"[ERROR] Failed to create service: {e}")
        return 0

    # Get site progress
    site_progress = get_site_progress(progress, domain)
    site_history = history.get(domain, {})

    # Check daily limit
    if site_progress['daily_sent'] >= DAILY_LIMIT:
        logger.info(f"[LIMIT] Daily limit ({DAILY_LIMIT}) reached for {domain}")
        return 0

    # Get URLs to submit
    urls_to_submit = get_urls_to_submit(site, progress, history)

    if not urls_to_submit:
        logger.info(f"[DONE] No URLs to submit for {domain}")
        return 0

    # Calculate how many we can send
    remaining_quota = DAILY_LIMIT - site_progress['daily_sent']
    urls_to_process = urls_to_submit[:remaining_quota]

    logger.info(f"[SEND] Sending {len(urls_to_process)} URLs (quota: {remaining_quota})")

    # Submit URLs
    sent_count = 0

    for i, url in enumerate(urls_to_process, 1):
        success, response = submit_url_to_indexing(service, url)

        if success:
            sent_count += 1
            site_progress['daily_sent'] += 1
            site_progress['last_index'] += 1

            # Update history
            if domain not in history:
                history[domain] = {}

            history[domain][url] = {
                'last_submitted': datetime.now().isoformat(),
                'lastmod': next((u.get('lastmod') for u in fetch_sitemap_urls(site['sitemap']) if u['url'] == url), None)
            }

            # Save progress periodically
            if sent_count % 10 == 0:
                save_progress(progress)
                save_history(history)
                logger.info(f"[PROGRESS] {sent_count}/{len(urls_to_process)} sent")

        elif response == 'QUOTA_EXCEEDED':
            logger.warning(f"[QUOTA] Stopping - daily limit reached")
            break

        # Rate limiting (be gentle with API)
        time.sleep(1)

    # Update progress
    site_progress['last_run'] = datetime.now().isoformat()

    # Check if first pass completed
    if site_progress['last_index'] >= site_progress['total_urls']:
        site_progress['completed_first_pass'] = True
        site_progress['last_index'] = 0
        logger.info(f"[COMPLETE] First pass completed for {domain}!")

    logger.info(f"[RESULT] Sent {sent_count} URLs for {domain}")
    logger.info(f"[STATUS] Progress: {site_progress['last_index']}/{site_progress['total_urls']}")

    return sent_count


def main():
    """Main function"""

    logger.info("[START] Google Instant Indexing")
    logger.info("=" * 60)

    # Load sites
    sites = load_sites()

    # Load progress and history
    progress = load_progress()
    history = load_history()

    total_sent = 0
    results = []

    for site in sites:
        if not site.get('enabled'):
            logger.info(f"[SKIP] Disabled: {site['name']}")
            continue

        if not site.get('indexing_credential'):
            logger.info(f"[SKIP] No indexing credential: {site['name']}")
            continue

        sent = process_site(site, progress, history)
        total_sent += sent

        results.append({
            'site': site['name'],
            'domain': site['domain'],
            'sent': sent,
            'progress': progress.get(site['domain'], {})
        })

        # Save after each site
        save_progress(progress)
        save_history(history)

        # Wait between sites
        time.sleep(2)

    # Final summary
    logger.info("=" * 60)
    logger.info("[SUMMARY] Instant Indexing Results")
    logger.info("=" * 60)

    for result in results:
        p = result['progress']
        status = "DONE" if p.get('completed_first_pass') else f"{p.get('last_index', 0)}/{p.get('total_urls', 0)}"
        logger.info(f"  {result['site']}: {result['sent']} sent | {status}")

    logger.info("=" * 60)
    logger.info(f"[TOTAL] {total_sent} URLs submitted")
    logger.info("[DONE] Instant indexing completed!")

    return 0


if __name__ == '__main__':
    sys.exit(main())
