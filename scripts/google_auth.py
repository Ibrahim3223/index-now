"""Google Search Console Authentication"""

import os
import json
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/webmasters',
    'https://www.googleapis.com/auth/webmasters.readonly'
]

SERVICE_ACCOUNT_FILE = Path(__file__).parent.parent / 'credentials' / 'search-console-482812-ef8276efec13.json'


def get_search_console_service():
    """Get authenticated Search Console API service"""

    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError(
            f"Service account file not found: {SERVICE_ACCOUNT_FILE}\n"
            "Please download from Google Cloud Console and place it in credentials/"
        )

    credentials = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES
    )

    service = build('searchconsole', 'v1', credentials=credentials)
    return service


def verify_access(site_url):
    """Verify that service account has access to site"""
    try:
        service = get_search_console_service()
        request = service.sites().get(siteUrl=site_url)
        response = request.execute()
        print(f"[OK] Access verified for {site_url}")
        return True
    except Exception as e:
        print(f"[FAIL] No access to {site_url}: {e}")
        return False


if __name__ == '__main__':
    # Test authentication
    from config import load_sites

    print("Testing Google Search Console Authentication...")
    print("=" * 60)

    sites = load_sites()

    for site in sites:
        if site.get('enabled'):
            verify_access(site['google_property'])
