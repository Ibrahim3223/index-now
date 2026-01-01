# Google Instant Indexing Kurulum Rehberi

## Nedir?

Google Instant Indexing API, URL'leri doğrudan Google'a göndermenizi sağlar. Normal crawl sürecini beklemeden sayfalarınızın indexlenmesini hızlandırır.

**Limit:** Her proje için günlük 200 URL

## Sistem Nasıl Çalışıyor?

```
Her Gün 00:05 UTC'de:
┌─────────────────────────────────────────────────────────┐
│  1. Sitemap'ten URL'leri çek                            │
│  2. Kaldığı yerden devam et (progress.json)             │
│  3. Günlük 200 URL gönder                               │
│  4. Progress'i kaydet                                   │
│  5. Tüm URL'ler bitti mi?                               │
│     ├─ Hayır → Ertesi gün devam                         │
│     └─ Evet → lastmod değişen veya 30 gün geçmiş        │
│               URL'leri tekrar gönder                    │
└─────────────────────────────────────────────────────────┘
```

## Kurulum Adımları

### Adım 1: Her Site İçin Google Cloud Projesi Oluştur

**Her site için ayrı proje = Her site için 200/gün limit**

1. https://console.cloud.google.com/ adresine git
2. Yeni proje oluştur:
   - `indexing-ruyatabirisozlugu`
   - `indexing-isimsozlugu`
   - `indexing-cicekansiklopedisi`
   - `indexing-burcsozlugu`
   - `indexing-mirasharitasi`

### Adım 2: Her Projede Indexing API'yi Etkinleştir

Her proje için:
1. APIs & Services > Library
2. "Web Search Indexing API" veya "Indexing API" ara
3. Enable

### Adım 3: Her Projede Service Account Oluştur

Her proje için:
1. IAM & Admin > Service Accounts
2. Create Service Account
   - Name: `indexing-bot`
3. Keys > Add Key > Create new key > JSON
4. İndirilen dosyayı şu isimle kaydet:
   - `indexing-ruyatabirisozlugu.json`
   - `indexing-isimsozlugu.json`
   - `indexing-cicekansiklopedisi.json`
   - `indexing-burcsozlugu.json`
   - `indexing-mirasharitasi.json`

### Adım 4: Search Console'a Service Account Ekle

**ÖNEMLİ:** Her site için, o sitenin service account email'ini Search Console'a Owner olarak ekle.

1. https://search.google.com/search-console
2. Site seç
3. Settings > Users and permissions
4. Add user
5. Service account email'ini yapıştır (örn: `indexing-bot@indexing-ruyatabirisozlugu.iam.gserviceaccount.com`)
6. Permission: **Owner**

**Bunu 5 site için tekrarla!**

### Adım 5: GitHub Secrets Ekle

GitHub repo > Settings > Secrets and variables > Actions

| Secret Name | Value |
|-------------|-------|
| `INDEXING_RUYATABIRISOZLUGU` | indexing-ruyatabirisozlugu.json içeriği |
| `INDEXING_ISIMSOZLUGU` | indexing-isimsozlugu.json içeriği |
| `INDEXING_CICEKANSIKLOPEDISI` | indexing-cicekansiklopedisi.json içeriği |
| `INDEXING_BURCSOZLUGU` | indexing-burcsozlugu.json içeriği |
| `INDEXING_MIRASHARITASI` | indexing-mirasharitasi.json içeriği |

### Adım 6: Lokal Test (Opsiyonel)

```bash
# Credential dosyalarını credentials/ klasörüne koy
cp indexing-*.json credentials/

# Test et
cd scripts
python google_instant_indexing.py
```

### Adım 7: GitHub Actions Çalıştır

1. Actions > Google Instant Indexing
2. Run workflow
3. Logları kontrol et

## Dosya Yapısı

```
credentials/
├── indexing-ruyatabirisozlugu.json
├── indexing-isimsozlugu.json
├── indexing-cicekansiklopedisi.json
├── indexing-burcsozlugu.json
└── indexing-mirasharitasi.json

data/
├── indexing_progress.json    # İlerleme durumu
└── indexing_history.json     # Gönderim geçmişi
```

## Progress Dosyası Örneği

```json
{
  "ruyatabirisozlugu.com": {
    "last_index": 1450,
    "total_urls": 9067,
    "last_run": "2024-12-30T10:00:00",
    "daily_sent": 200,
    "completed_first_pass": false
  }
}
```

## Tahmini Süre

| Site | URL Sayısı | İlk Geçiş Süresi |
|------|------------|------------------|
| ruyatabirisozlugu.com | 9,067 | ~46 gün |
| isimsozlugu.net | 2,523 | ~13 gün |
| cicekansiklopedisi.com | 1,793 | ~9 gün |
| burcsozlugu.com | 360 | ~2 gün |
| mirasharitasi.com | 18,925 | ~95 gün |

**Toplam: ~165 gün (ilk geçiş)**

## Sık Sorulan Sorular

### Limit proje başına mı, hesap başına mı?
**Proje başına.** Her Google Cloud projesi için ayrı 200/gün limit.

### İlk geçiş bittikten sonra ne olacak?
Sistem otomatik olarak:
- `lastmod` tarihi değişen URL'leri tekrar gönderir
- 30 günden eski gönderimli URL'leri tekrar gönderir

### Quota hatası alırsam?
Sistem otomatik durur ve ertesi gün devam eder.

### Hangi URL'ler gönderildi görebilir miyim?
`data/indexing_history.json` dosyasında tüm geçmiş var.

## Önemli Notlar

- Indexing API öncelikle JobPosting ve BroadcastEvent için tasarlanmış ama diğer içerikler için de çalışır
- Google'ın indexleme garantisi yok, sadece crawl önceliği verir
- Spam yapma - aynı URL'leri sürekli gönderme (sistem bunu otomatik engeller)
