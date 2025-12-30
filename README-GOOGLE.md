# Google Indexing Setup Guide

## Step 1: Create Google Service Account

### 1.1 Go to Google Cloud Console
https://console.cloud.google.com/

### 1.2 Create New Project
- Project name: "SEO Automation"
- Click "Create"

### 1.3 Enable Search Console API
- Navigate to "APIs & Services" > "Library"
- Search for "Google Search Console API"
- Click "Enable"

### 1.4 Create Service Account
- Go to "IAM & Admin" > "Service Accounts"
- Click "Create Service Account"
- Name: "seo-automation"
- Click "Create and Continue"
- Role: "Owner" (for testing, restrict later)
- Click "Done"

### 1.5 Create Key
- Click on the service account
- Go to "Keys" tab
- Click "Add Key" > "Create new key"
- Choose "JSON"
- Download the file
- Rename to `service-account.json`
- Place in `credentials/` folder

### 1.6 Get Service Account Email
- Note the email: `seo-automation@project-id.iam.gserviceaccount.com`

## Step 2: Add Service Account to Search Console

### For EACH site:

1. Go to https://search.google.com/search-console
2. Select property (e.g., `ruyatabirisozlugu.com`)
3. Settings > Users and permissions
4. Click "Add user"
5. Paste service account email
6. Permission: "Owner"
7. Click "Add"

**Repeat for all 6 sites!**

## Step 3: Add GitHub Secret

1. Go to GitHub repo
2. Settings > Secrets and variables > Actions
3. New repository secret
4. Name: `GOOGLE_SERVICE_ACCOUNT`
5. Value: Paste ENTIRE contents of `service-account.json`
6. Click "Add secret"

## Step 4: Test

### Local test:
```bash
cd scripts
python google_sitemap_submit.py
```

### GitHub Actions test:
1. Go to Actions tab
2. Select "Google Indexing - Daily"
3. Click "Run workflow"
4. Check logs

## Available Scripts

| Script | Description |
|--------|-------------|
| `google_auth.py` | Authentication module for Google APIs |
| `google_sitemap_submit.py` | Submit sitemaps to Google Search Console |
| `google_url_inspection.py` | Inspect URLs and check indexing status |
| `google_bulk_indexing.py` | Aggressive multi-pronged indexing strategy |

## GitHub Actions Workflows

| Workflow | Schedule | Description |
|----------|----------|-------------|
| `google-indexing-daily.yml` | Daily 08:00 UTC | Standard/aggressive indexing |
| `google-sitemap-submit.yml` | Weekly (Monday) | Sitemap submission |
| `google-inspection.yml` | Weekly (Sunday) | URL inspection report |

## Expected Results

- Sitemaps submitted: Immediate
- Google crawling starts: 1-7 days
- Full indexing: 2-4 weeks (for 10,000+ pages)

## Acceleration Tips

1. **Submit sitemaps weekly**
2. **Use aggressive mode monthly**
3. **Monitor Google Search Console**
4. **Fix crawl errors immediately**
5. **Add internal links**
6. **Get quality backlinks**

## Rate Limits

Google API has strict rate limits:
- 2000 requests per day (per project)
- 600 requests per minute (per project)

The scripts are designed to respect these limits.

## Important Notes

- Google API has rate limits
- Don't abuse aggressive mode
- Focus on quality content
- Be patient (indexing takes time)

## Troubleshooting

### "No access to site" error
- Make sure service account email is added to Search Console
- Verify the property URL format matches (e.g., `sc-domain:example.com`)

### "API not enabled" error
- Go to Google Cloud Console
- Enable "Google Search Console API"

### "Quota exceeded" error
- Wait 24 hours
- Reduce `max_urls` parameter
- Space out workflow runs

## File Structure

```
seo-automation/
├── .github/workflows/
│   ├── google-indexing-daily.yml
│   ├── google-sitemap-submit.yml
│   └── google-inspection.yml
├── scripts/
│   ├── config.py
│   ├── utils.py
│   ├── google_auth.py
│   ├── google_sitemap_submit.py
│   ├── google_url_inspection.py
│   └── google_bulk_indexing.py
├── credentials/
│   ├── service-account.json (gitignore!)
│   └── .gitkeep
├── data/
│   ├── sites.json
│   ├── google_indexed_urls.json
│   └── google_pending_urls.json
├── logs/
├── requirements.txt
└── README-GOOGLE.md
```
