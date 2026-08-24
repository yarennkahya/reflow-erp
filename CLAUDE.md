# Proje: Kahve Kavurma & Dağıtım ERP + AI Karar Destek Platformu (ad TBD)

## Ne inşa ediyoruz
Özel kahve kavurma/dağıtım işletmesi için uçtan uca bir ERP platformu. Yeşil kahve
tedarikçilerinden alım, harman/kavurma üretimi (BOM tabanlı), toptan (kafelere B2B) ve
perakende (B2C) satış kanallarını tek sistemde birleştiren; üzerine RAG + function calling
tabanlı bir AI karar destek katmanı eklenen bir platform.

Staj projesi olarak başladı, gerçekten kullanılabilir/ürünleşebilir kalitede geliştiriliyor.
Sabit bir bitiş tarihi yok — kaliteden ödün vermek yerine gerekirse sarkabilir.

NOT: Bu proje başlangıçta bir "surplus/bağış" senaryosu (Reflow) olarak tasarlanmıştı,
sonradan kahve kavurma senaryosuna geçildi. Docker/Django/PostgreSQL/Celery altyapısı ve
Business/Product/Lot/StockMovement modelleri o aşamadan aynen taşındı. Partner ve
Distribution modelleri (bağışa özgüydü) kaldırıldı.

## Teknoloji yığını
- Backend: Python, Django 5.1
- Veritabanı: PostgreSQL + pgvector (embeddings için ayrı vector DB YOK)
- Önbellek & kuyruk: Redis
- Arka plan görevleri: Celery (+ Celery Beat)
- Konteynerleştirme: Docker, docker-compose
- Web sunucusu: NGINX + Gunicorn
- AI: OpenAI API (embeddings + chat completions + function calling)
- İzleme: Sentry (MVP), Grafana (stretch)

## Mimari kararlar — bunlara sadık kal
1. **Stok asla doğrudan güncellenmez.** Her değişiklik bir `StockMovement` (ledger) kaydı
   olarak eklenir. Bu, hangi senaryo olursa olsun (bağış ya da kahve) değişmedi.
2. **Lot bazlı tazelik takibi zorunlu.** Kavrulmuş kahvenin tazelik penceresi dar (kavurma
   sonrası ~3-14 gün en iyi lezzet). Toptan siparişleri karşılarken eski (ama hâlâ taze)
   lot'lar önce kullanılır (stok rotasyonu / FIFO'ya benzer mantık).
3. **BOM tabanlı üretim (YENİ).** `Recipe`/`Blend` bir harmanın hangi yeşil kahve
   lot'larından hangi oranda oluştuğunu tanımlar. `RoastBatch`, bir üretim emridir: yeşil
   kahve lot'larından `StockMovement` OUT hareketi düşer, kavrulmuş ürün için yeni bir
   `Lot` ve `StockMovement` IN hareketi oluşturur.
4. **AI katmanı function calling ile kontrollü erişim kullanır.** LLM asla doğrudan
   veritabanına yazmaz; sadece tanımlı, yetkilendirilmiş fonksiyonları çağırabilir.
5. **Django app yapısı modüler monolit.** `inventory` (tedarik/stok), `production`
   (harman/kavurma), `sales` (müşteri/sipariş), `finance`, `ai_layer` — hepsi aynı
   PostgreSQL veritabanını paylaşır.
6. **Foreign key silme davranışı:** Geçmiş hareket/işlem kayıtlarına referans veren
   nesnelerde `on_delete=models.PROTECT` kullan, `CASCADE` değil.

## Modüller
**MVP kapsamında (✅ mutlaka bitmeli):**
- Tedarik & Stok: `Business` (tedarikçi), `Product`, `Lot`, `StockMovement` (zaten var,
  taşındı) — sadece etiketleme/choice güncellemesi gerekiyor
- Üretim (YENİ): `Recipe`/`Blend`, `RoastBatch` — BOM mantığı
- Satış (YENİ): `Customer` (toptan/perakende), `Order`
- Basit finans (gelir-gider)
- AI katmanı: RAG + embeddings/pgvector + function calling (tazelik uyarısı, talep
  tahmini, tedarikçi/müşteri analizi)

**Stretch goal (🔶 zaman kalırsa):**
- İK, ileri RBAC, TR/EN dil desteği, dark/light tema, Grafana/Prometheus

## Geçiş notu (bağıştan kahveye — kaldırılanlar)
- `Partner` modeli kaldırıldı (bağış ortağı kavramı kahvede yok)
- `Distribution` modeli kaldırıldı
- `decide_channel()` / `apply_distribution()` sadeleştirilecek: DONATION dalı olmadan,
  sadece tazelik durumuna göre "normal sat / öncelikli-indirimli sat / ıskarta" kararı
  verecek şekilde yeniden yazılacak

## Yol haritası (güncel, esnek)
1. ~~Kurulum, docker-compose, temel modeller~~ ✅ tamamlandı
2. ~~Çekirdek stok/lot akışı, Celery otomasyonu~~ ✅ tamamlandı (bağış senaryosunda)
3. Partner/Distribution temizliği, tazelik mantığının sadeleştirilmesi
4. Üretim modülü: Recipe/Blend, RoastBatch (BOM)
5. Satış modülü: Customer, Order (toptan + perakende)
6. AI katmanı: embedding, pgvector, RAG, function calling
7. Finans, deployment, test, demo

## Kod kuralları
- Model/değişken/fonksiyon adları İngilizce, yorumlar Türkçe olabilir.
- Her yeni model için Django admin kaydı ekle.
- Migration'ları küçük ve açıklayıcı tut.

## Claude Code için not
Bu dosyayı her session başında oku. Önemli bir karar değişirse bu dosyayı güncelle.