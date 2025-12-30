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

CREDENTIALS_DIR = Path(__file__).parent.parent / 'credentials'

# Check multiple possible credential file names
CREDENTIAL_FILES = [
    'service-account.json',  # GitHub Actions
    'search-console-482812-ef8276efec13.json',  # Local development
]


def get_service_account_file():
    """Find the service account file"""
    for filename in CREDENTIAL_FILES:
        filepath = CREDENTIALS_DIR / filename
        if filepath.exists():
            return filepath
    return None


def get_search_console_service():
    """Get authenticated Search Console API service"""

    service_account_file = get_service_account_file()

    if not service_account_file:
        raise FileNotFoundError(
            f"Service account file not found in {CREDENTIALS_DIR}\n"
            f"Expected one of: {CREDENTIAL_FILES}\n"
            "Please download from Google Cloud Console and place it in credentials/"
        )

    credentials = service_account.Credentials.from_service_account_file(
        str(service_account_file),
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
