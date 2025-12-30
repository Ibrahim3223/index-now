"""Configuration module for SEO Automation"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
SITES_FILE = DATA_DIR / 'sites.json'


def load_sites():
    """Load sites configuration from JSON file"""

    if not SITES_FILE.exists():
        raise FileNotFoundError(f"Sites file not found: {SITES_FILE}")

    with open(SITES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('sites', [])


def get_enabled_sites():
    """Get only enabled sites"""

    sites = load_sites()
    return [s for s in sites if s.get('enabled', False)]


def get_site_by_domain(domain):
    """Get site configuration by domain"""

    sites = load_sites()
    for site in sites:
        if site.get('domain') == domain:
            return site
    return None
