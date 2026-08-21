# Proje: Surplus/Bağış Yönetimi + AI Karar Destek Platformu (ad TBD)

## Ne inşa ediyoruz
İşletmelerin (market, restoran, üretici) SKT'si yaklaşan/surplus ürünlerini toplayan; bunları
iki kanala — **indirimli B2C satış** veya **gıda bankası/dernek bağışı** — yönlendiren; üzerine
RAG + function calling tabanlı bir AI karar destek katmanı eklenen, uçtan uca bir ERP platformu.

Staj projesi olarak başladı, gerçekten kullanılabilir/ürünleşebilir kalitede geliştiriliyor.
Sabit bir bitiş tarihi yok — kaliteden ödün vermek yerine gerekirse sarkabilir.

## Teknoloji yığını
- Backend: Python, Django
- Veritabanı: PostgreSQL + **pgvector** (embeddings için ayrı vector DB YOK, pgvector yeterli)
- Önbellek & kuyruk: Redis
- Arka plan görevleri: Celery (+ Celery Beat)
- Konteynerleştirme: Docker, docker-compose
- Web sunucusu: NGINX + Gunicorn
- AI: OpenAI API (embeddings + chat completions + function calling)
- İzleme: Sentry (MVP), Grafana (stretch)
- Frontend: Django Template + Bootstrap + vanilla JS (MVP), gerekirse sonradan zenginleştirilir

## Mimari kararlar — bunlara sadık kal
1. **Stok asla doğrudan güncellenmez.** Her değişiklik bir `StockMovement` (ledger) kaydı
   olarak eklenir (`quantity -= 5` gibi bir satır YAZMA). `StockLevel` sadece performans
   cache'idir; gerçek kaynak (source of truth) her zaman `StockMovement`'tır.
2. **FIFO zorunlu.** Lot/SKT bazlı stokta, paket/sipariş oluştururken SKT'si en yakın olan
   lot önce kullanılır.
3. **Kanal yönlendirme kural tabanlı, optimizasyon değil (MVP için).** "Bu ürün bağışa mı
   satışa mı gitsin" basit if/else kurallarıyla çözülür (örn. SKT eşiği + ortak kapasitesi).
   Gerçek rota optimizasyonu (VRP) stretch goal — MVP'de "en yakın uygun depo/ortak" ataması
   yeterli.
4. **AI katmanı function calling ile kontrollü erişim kullanır.** LLM asla doğrudan
   veritabanına yazmaz veya SQL üretmez; sadece tanımlı, yetkilendirilmiş fonksiyonları
   çağırabilir (örn. `check_expiring_stock()`, `get_partner_capacity()`).
5. **Django app yapısı modüler monolit.** Her iş alanı ayrı bir app: `crm`, `inventory`,
   `sales`, `donations`, `finance`, `ai_layer`, vb. Hepsi aynı PostgreSQL veritabanını
   paylaşır.
6. **Foreign key silme davranışı:** Geçmiş hareket/işlem kayıtlarına referans veren
   nesnelerde `on_delete=models.PROTECT` kullan, `CASCADE` değil — tarihsel veri kaybolmasın.

## Modüller
**MVP kapsamında (✅ mutlaka bitmeli):**
- CRM (tedarikçi işletme + son kullanıcı/dernek profili)
- Stok & Lot/SKT (FIFO, kritik SKT uyarısı)
- Satış/Bağış yönlendirme (kural tabanlı)
- Basit finans (gelir-gider, şeffaflık özeti)
- AI katmanı (RAG + embeddings/pgvector + function calling, SKT+ihtiyaç eşleştirme)

**Stretch goal (🔶 zaman kalırsa):**
- İK (gönüllü/lojistik personeli yönetimi)
- Gerçek rota optimizasyonu (VRP)
- Ödeme gateway entegrasyonu
- İleri RBAC, TR/EN dil desteği, dark/light tema, Grafana/Prometheus

## Yol haritası (esnek, sarkabilir)
1. Kurulum: docker-compose, Django proje iskeleti, temel modeller
2. Çekirdek ERP akışı: CRM, stok/SKT, kural tabanlı yönlendirme, Django admin
3. AI katmanı: chunk'lama, embedding, pgvector, RAG, function calling
4. Celery görevleri (günlük SKT taraması) + finans
5. Deployment: docker-compose ile NGINX+Gunicorn+PostgreSQL+Redis, Sentry
6. Test, demo verisi, sunum hazırlığı

## Kod kuralları
- Model/değişken/fonksiyon adları İngilizce, yorumlar Türkçe olabilir.
- Her yeni model için Django admin kaydı ekle (ücretsiz yönetim paneli).
- Migration'ları küçük ve açıklayıcı tut.

## Claude Code için not
Bu dosyayı her session başında oku, yukarıdaki mimari kararlara sadık kal. Önemli bir karar
değişirse (kullanıcıyla veya claude.ai'daki planlama sohbetinde), bu dosyayı güncelle.
