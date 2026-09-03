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

## Tasarım sistemi (Odoo dili) — bunlara uy

Tüm sunum katmanı Odoo'nun tasarım diliyle yeniden yazıldı. Eski `meridian.css`
ve `g-*` sınıfları **silindi**; sayfa içi `<style>` bloğu **kalmadı**.

### Sert kurallar
1. **Hiçbir şablonda `<style>` yok.** Yeni stil `static/css/odoo-web.css`'e eklenir.
2. **Hiçbir şablonda mantık içeren `<script>` yok.** Sadece
   `<script type="application/json">` veri adacığı olur; davranış `static/js/o-*.js`'e yazılır.
3. **Renk için literal hex yazma.** Her renk `var(--o-*)` token'ından okunur; aksi
   halde dark mode'da bozulur.
4. **Çok satırlı `{# #}` yorumu kullanma** — Django'da `{# #}` tek satırlıktır,
   çok satırlısı ekrana basılır. Çok satırlı için `{% comment %}` kullan.
5. **Rozet üretme.** Durum göstergeleri yalnızca `{% ui_badge obj "alan" %}` ile
   basılır; renk eşlemesi `dashboard/badges.py`'de tek yerdedir.
6. **Navigasyon `dashboard/navigation.py`'deki registry'den gelir.** Yeni bir rota
   eklediğinde ilgili `MenuItem.routes` demetine ekle, yoksa breadcrumb ve aktif
   menü çalışmaz.

### Katmanlar
- `static/css/odoo-core.css` — token'lar (light/dark), Bootstrap köprüsü, reset, tipografi
- `static/css/odoo-web.css` — app shell, görünümler, bileşenler
- `static/css/odoo-public.css` — landing + giriş sayfası
- `static/js/o-*.js` — çekirdek (`o-core`, `o-theme`, `o-appbar`, `o-ajax`,
  `o-notifications`, `o-search`, `o-confirm`) her sayfada; `o-x2many`, `o-kanban`,
  `o-charts`, `o-meetings`, `o-chat`, `o-public` sayfaya özel
- `templates/ui/` — bileşen partial'ları; `dashboard/templatetags/ui.py` — tag'ler
  (`builtins` olarak kayıtlı, `{% load ui %}` gerekmez)

### Palet: Espresso + Bakır
Primary `#6B4632`, aksan (bakır) `#C87941`, app bar `#3A2A20`, sıcak nötr yüzeyler.
Dark mode `[data-bs-theme="dark"]` ile primary'yi **açar** (`#C8A18A`).
Yoğunluk gerçek Odoo ölçüsünde: 13px font, 30px tablo satırı, 3–4px radius, tek gölge.

### Görünüm mimarisi
- Liste/kanban/takvim/grafik `?view=` parametresiyle **sunucu tarafında** seçilir
  (`dashboard/views_helpers.pick_view`), şablon `{% include view_template %}` yapar.
- Kanban kolonları `dashboard/grouping.group_by_choice` ile üretilir.
- Takvimler `dashboard/calendars.py`'den gelir: tek günlük olaylar için `month_grid`,
  aralık olaylar (izinler) için `month_grid_spans`.
- AJAX filtreleyen sayfalar `{% block region_attr %} data-ajax-region{% endblock %}`
  doldurur; hedef `#o-view`'dur, böylece control panel ile görünüm birlikte yenilenir.
  **Bölge içinde yalnızca deklaratif Bootstrap** (`data-bs-toggle`) kullan;
  `new bootstrap.X()` örneği swap'ta ölür. Bölge değişince `o:region-replaced`
  olayı yayınlanır, widget'lar buna abonedir.

### i18n
Gerçek Django i18n. **msgid'ler Türkçe**, `locale/en/LC_MESSAGES/django.po` yalnızca
İngilizce kataloğu tutar. `{% translate %}` / `{% blocktranslate %}` kullan; model
`TextChoices` etiketleri `gettext_lazy` ile sarılı (lazy şart).
Tuzak: `makemessages`, tag keyword argümanlarındaki dizeleri **çıkarmaz** —
`{% translate "…" as t %}{% ui_empty title=t %}` kalıbını kullan.

### Geliştirme döngüsü
- Şablon ve CSS/JS değişiklikleri anında yansır (DEBUG'ta şablon önbelleği kapalı,
  gunicorn `--reload`), **ama statikler toplanmalı**:
  `docker compose exec web python manage.py collectstatic --noinput`
  Atlanırsa NGINX 404 döner ve sayfa sessizce stilsiz açılır.
- Çeviri değişince: `makemessages -l en` → çevir → `compilemessages`.
- Her değişiklikten sonra: `docker compose exec web python manage.py smoke`
  (registry'deki her rotayı 5 demo rolüyle gezer, şablon sağlığını da denetler).

## Claude Code için not
Bu dosyayı her session başında oku. Önemli bir karar değişirse bu dosyayı güncelle.