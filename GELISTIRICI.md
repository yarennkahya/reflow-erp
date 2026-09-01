# Geliştirici Notları — Odoo Tarzı Arayüz Yeniden Yazımı

Bu belge, sunum katmanının baştan yazılmasında **ne yapıldığını**, **hangi teknolojinin
neden seçildiğini** ve **nasıl kullanıldığını** özetler.

> Tasarım sistemine dair **uyulması zorunlu kurallar** `CLAUDE.md` → "Tasarım sistemi
> (Odoo dili)" bölümündedir. Bu dosya arka planı ve gerekçeleri anlatır.

---

## 1. Neden yeniden yazıldı

Ölçülen başlangıç durumu:

- `meridian.css` (2.741 satır) olgun bir sistem tanımlıyordu ama **66 şablondan yalnızca
  4'ü kullanıyordu**. Kanonik bileşenlerini (`.g-data-card`, `.g-subnav`, `.g-empty-state`)
  **sıfır şablon** çağırıyordu.
- **44 şablon** kendi minified `<style>` bloğunu taşıyor, aynı bileşenleri tekrar icat
  ediyordu: `.data-card` ×26, `.empty-state` ×20, `.form-card` ×11, `*-subnav` ×10.
- Şablonlarda **381 inline `style=`** ve **70 farklı sabit hex** vardı; hiçbiri token'dan
  geçmediği için **dark mode'da bozuluyordu** (bu yüzden 103 ayrı `dark-mode` seçicisi).
- Navigasyon `base.html`'de **29 boş `{% block nav_* %}`** slotuyla yürüyordu; 53 şablondan
  48'i dolduruyor, 3'ü hiç doldurmuyordu.
- Pagination, grafik, modal, breadcrumb, custom template tag **hiç yoktu**.

---

## 2. Sonuç (ölçülmüş)

| | Önce | Sonra |
|---|---|---|
| Şablon satırı | 7.586 | 5.258 |
| `base.html` | 1.011 | 96 |
| Landing | 1.921 | 245 |
| Sayfa içi `<style>` | 44 dosya | **0** |
| Sabit hex renk | 70 farklı | **0** |
| Inline `style=` | 381 | 10 (hepsi çalışma anı değeri) |
| CSS / JS dosyası | 1 / 0 | 3 (2.308 satır) / 14 (1.436 satır) |
| Bileşen partial'ı | 0 | 23 |
| Template tag/filtre | 0 | 20 |

---

## 3. Teknoloji seçimleri — ne, neden, nasıl

### Bootstrap 5.3.3 — **korundu, atılmadı**
- **Neden:** Odoo'nun kendi web istemcisi de Bootstrap 5 üzerine kurulu; "Odoo görünümü"
  zaten Bootstrap'e giydirilmiş bir temadır. Ayrıca burada load-bearing'di: `row/col-*`
  42 şablonda, `btn` 57'de, `badge` 26'da. Dropdown/modal/tab/collapse JS'i de bedava.
- **Nasıl:** `--bs-*` CSS değişkenleri kendi token'larımıza köprülendi. Bootstrap'in
  **değişkenleştirmediği** yerler (`.btn-primary` literal hex derler, `.form-control:focus`
  sabit mavi, `.form-select` ok SVG'si data-URI içinde renk taşır) açıkça ezildi — yoksa
  "neden hâlâ mavi" sorununun kaynağı bunlar olurdu.

### Dark mode: `[data-bs-theme]` — **`html.dark-mode` sınıfı atıldı**
- **Neden:** Bootstrap 5.3 dark mode'u yerel olarak destekliyor. Eski yaklaşım 103 ayrı
  seçici gerektiriyordu çünkü sayfalar ham hex kullanıyordu.
- **Nasıl:** Her renk `var(--o-*)` token'ından okunur; dark blok yalnızca token'ları yeniden
  tanımlar. **Kritik:** dark'ta primary *açılır* (`#6B4632` → `#C8A18A`), çünkü koyu zeminde
  okunmaz. Bu yüzden hiçbir bileşen literal hex yazmaz.

### Build adımı **yok** — elle yazılmış CSS + saf JS
- **Neden:** Projede Node yok, `package.json` yok. Bir build zinciri eklemek dağıtımı
  kırılganlaştırırdı. Odoo yoğunluğu (13px, 30px satır) zaten elle ayarlanacak bir şey.
- **Nasıl:** 3 CSS dosyası (`odoo-core` / `odoo-web` / `odoo-public`), 14 IIFE JS dosyası,
  tek global: `window.O`. ES modülü kullanılmadı — NGINX arkasında CORS/MIME sivri uçları
  getirir, karşılığı sıfır.

### Chart.js 4 (UMD, CDN) — grafik görünümü
- **Neden:** Tek dosya, build gerektirmez, `<canvas>` tabanlı, renkleri JS'ten kontrol
  edilebilir. ApexCharts daha ağır ve stilini ezmek zor; D3'te grafik primitifi yok.
- **Nasıl:** Yalnızca 3 grafik sayfasında yüklenir. Veri `<script type="application/json">`
  adacığıyla gelir; `o-charts.js` renkleri `getComputedStyle`'dan CSS token'ı olarak okur ve
  `o:theme` olayında yeniden çizer — **tema değişince grafikler bedavaya renk değiştirir.**

### Django i18n — **client-side sözlük atıldı**
- **Neden:** Eski sistem kırıktı: şablonlarda 150+ `data-i18n` anahtarı vardı ama sözlükte
  yalnızca 36'sı; gerisi sessizce hiçbir şey yapmıyordu. TreeWalker `INPUT/SELECT` atladığı
  için `<option>` etiketleri ve `placeholder`'lar hiç çevrilmiyordu. Ayrıca 15 `TextChoices`
  sınıfının etiketleri Python'daydı — istemci JS'i onları çeviremezdi.
- **Nasıl:** **msgid'ler Türkçe**, yalnızca `locale/en/` kataloğu var (650 dize, 0 çevrilmemiş,
  0 fuzzy). `LocaleMiddleware` + `set_language` POST formu. Model etiketleri `gettext_lazy`
  ile sarılı (**lazy şart** — düz `gettext` build zamanı dilini içine gömer).
- **Tuzak:** `makemessages`, tag keyword argümanlarındaki dizeleri **çıkarmaz**. Kalıp:
  `{% translate "…" as t %}{% ui_empty title=t %}`

### Pointer Events — kanban sürükle-bırak
- **Neden:** HTML5 drag&drop **dokunmatikte çalışmaz**. Kütüphane eklemek build gerektirirdi.
- **Nasıl:** Farede 5px hareket, dokunmatikte 250ms basılı tutma sürüklemeyi başlatır
  (hemen başlatmak panoyu kaydırmayı imkânsız kılardı). İyimser taşıma; sunucu reddederse
  kart eski yerine döner ve gerekçe toast olur.

---

## 4. Mimari kararlar

### Navigasyon registry (`dashboard/navigation.py`)
- 29 boş `{% block nav_* %}` slotunun yerine **11 `AppDef` + 24 `MenuItem`**.
- **~90 url_name'in tamamı** bir `routes` demetine bağlı → detay/form sayfaları da doğru
  menüyü aktif gösterir, breadcrumb kendiliğinden üretilir.
- `reverse()` `NoReverseMatch`'i **yutar**: `resolver_match` 404/500'de `None` olur ve
  registry'deki tek bir yazım hatası aksi halde **her sayfayı** 500'e düşürürdü.
- Neden `dashboard/`? Nav inventory'nin işi değil; `config` app değil (templatetags
  barındıramaz); yeni app gereksiz. `dashboard` zaten kurulu ve web istemcisinin kendisi.

### Bileşen kütüphanesi (`dashboard/templatetags/ui.py` + `templates/ui/`)
- 20 tag/filtre, 23 partial. `TEMPLATES['OPTIONS']['builtins']` ile kayıtlı →
  **hiçbir şablonda `{% load %}` yok** (66 satır boilerplate ve bütün bir hata sınıfı gitti).
- `{% ui_field %}` en büyük kazanç: ~60 elle yazılmış tekrarı öldürdü. Sınıfı widget tipinden
  türetir ve **merge etmez, değiştirir** → 5 `forms.py`'deki `setdefault('class', …)`
  döngüleri ölü koda dönüştü ve silindi.

### Rozet birleştirme (`dashboard/badges.py`)
- Rozet CSS sınıfı **4 view modülünde ~18 çağrı noktasında** elle hesaplanıyordu, üstelik
  iki farklı biçimde. Hepsi **20 girişlik tek haritaya** indi.
- `{% ui_badge obj "alan" %}` anahtarı `obj._meta`'dan, etiketi `get_FIELD_display()`'den
  türetir. CSS altı kural, hepsi token'dan → dark mode bedava doğru.

### Görünüm mimarisi: `?view=` sunucu tarafında
- Client-side tab **değil**, çünkü (a) mevcut `data-ajax-region` makinesiyle bedavaya
  birleşir, (b) bookmark'lanabilir ve geri tuşu doğru çalışır, (c) DOM'da veri kopyalanmaz.
- AJAX hedefi `base.html`'deki `#o-view` → control panel (arama + sayfalayıcı + görünüm
  değiştirici) **görünümle birlikte** yenilenir; Odoo'nun davranışı budur.

### AJAX bölge çerçevesi — **taşındı, yeniden yazılmadı**
- Çalışan 280 satırlık kod `base.html`'den `o-ajax.js`'e taşındı; 8 partial ona bağlıydı,
  UI yeniden yazımı sırasında onu da yeniden yazmak patlama yarıçapını ikiye katlardı.
- Tek işlevsel ekleme: `replaceWith()` sonrası **`o:region-replaced` olayı**. Bu **gizli bir
  hatayı** kapattı — eskiden bölge değişince içindeki hiçbir şey yeniden kurulmuyordu;
  kanban ve grafikler tam o bölgelerin içine girdiği için artık gerçek bir hataydı.
- **Kural:** `data-ajax-region` içinde yalnızca deklaratif Bootstrap (`data-bs-toggle`).
  `new bootstrap.X()` örneği swap'ta ölür.

### Dinamik satırlar: üç uygulama → tek widget (`o-x2many.js`)
- Satın alma (klonlama + tedarikçi→ürün filtresi), satış (klonlama), reçete (JS template
  literal + %100 doğrulayıcı) ayrı ayrı yazılmıştı.
- **Load-bearing input adları korundu** çünkü JS'te değil, sunucunun bastığı satır
  markup'ında yaşıyorlar → `request.POST.getlist('product')` gibi çağrılar aynen çalışır.
  **Sıfır Python değişikliği.** Doğrulaması görsel değil, **üç formda gerçek POST turu**.

---

## 5. Eklenen işlevler

- **Kanban sürükle-bırak** — 5 panoda (CRM fırsat, işe alım, çalışan, satın alma, satış).
  Her geçiş **servis katmanından** geçer, alan doğrudan yazılmaz.
  - 3 pano **bilerek salt okunur** ve sebebini panoda yazar: envanter tazeliği SKT'den
    *hesaplanır*, fatura durumu ödemelerden doğar, kalite sonucu kontrolü yapan kişiyi
    zorunlu kılar. Sürüklemek veriyi bozardı.
- **İşe alım aşama ilerletme** — backend'de hiç yoktu. Son adım (İşe Alındı)
  `hire_candidate`'ten geçer: Employee oluşur, kontenjan dolarsa pozisyon `filled` olur.
- **Satış siparişi durum aksiyonları** — "Karşıla" `fulfill_order`'dan geçer (stok hareketi
  üretir); iptal **yalnızca beklemedeki** siparişlerde (karşılanmışı iptal etmek hareketleri
  geri almayı gerektirir — o iade akışının işi).
- **Fatura önizleme + gönderme** — satış listesinde büyüteç bir `<dialog>`'a parça yükler;
  zarf ikonu Celery göreviyle müşteriye e-posta atar.
- **Yeni müşteri ekleme** — satış modülünde hiç yoktu. `?next=` ile sipariş formundan
  gidilip dönülür ve müşteri **önceden seçili** gelir. `CustomerForm` `sales`'a taşındı
  (modelin sahibi orası; crm oradan import eder — bağımlılık yönü zaten doğruydu).
- **Kanban / takvim / grafik görünümleri** — 9 sayfada. İzin takvimi **aralık** olayları
  çizer (`month_grid_spans`), diğerleri tek günlük (`month_grid`).
- **Pagination** — 9 modülde (önceden hiç yoktu; `audit` tüm tabloyu basıyordu).

---

## 6. Yol boyunca düzeltilen gerçek hatalar

Tasarımdan bağımsız, ama işi engelleyen kusurlar:

- **`collectstatic` Docker build'de hiç çalışmıyordu.** NGINX `/static/`'i volume'dan servis
  ediyor; mevcut CSS'in çalışmasının tek sebebi bir kez elle toplanmış olmasıydı. Eklenecek
  her dosya 404 verecekti. → Dockerfile'a eklendi.
- **`.env` imaja gömülüyordu** (`COPY . .`), içinde `DJANGO_SECRET_KEY` ve
  `EMAIL_HOST_PASSWORD`. Compose zaten `env_file` ile çalışma anında veriyor.
  → `.dockerignore` eklendi (context 1.5 MB → 0.9 MB).
- **PostgreSQL id dizileri bozuktu** — sipariş oluşturma `IntegrityError` ile tamamen
  kırıktı. 39 sequence senkronlandı.
- **`dashboard_view` `module_access`'i gölgeliyordu** → `/dashboard/`'da AI, Takvim ve
  Denetim her zaman kilitli görünüyordu.
- **`/profile/` `login_required` değildi** → anonim GET 500 veriyordu.
- **Django `cached.Loader`'ı `DEBUG=True`'da bile kullanıyordu** → her şablon düzenlemesi
  restart gerektiriyordu. `APP_DIRS` yerine açık loader listesi kondu.
- **NGINX `expires 1h` yüzünden CSS değişiklikleri görünmüyordu** → `ASSET_VERSION`
  (static/ altındaki en yeni mtime) ile `?v=` cache-busting. DEBUG'ta her istekte taze.
- `config/urls.py` `auth.urls`'ü iki kez include ediyordu; `STATIC_URL` iki kez tanımlıydı;
  `sales.Order.Status` etiketleri tek istisna olarak İngilizceydi (migration `0005`);
  `celerybeat-schedule` repoda takip ediliyordu; 2 ölü şablon vardı.

---

## 7. Doğrulama

Projede test paketi yoktu (`*/tests.py` boş). Eklenen:

```bash
docker compose exec web python manage.py smoke
```

- Registry'deki **her rotayı 5 demo rolüyle** gezer → **320 istek**.
- Yakaladığı iki hata sınıfı bu yeniden yazımın tam olarak ürettikleridir:
  bayat registry girdisinden `NoReverseMatch`, ve context değişkeni kaybeden şablon.
- Ayrıca **şablon sağlığı** denetler: sayfa içi `<style>` ve **çok satırlı `{# #}` yorumu**
  (Django'da `{# #}` tek satırlıktır; çok satırlısı ekrana basılır — bu hata iki kez oldu).

Tarayıcı doğrulaması (Playwright, Chromium): 60 rota × 3 genişlik (390 / 768 / 1440) otomatik
kusur taraması — yatay taşma, viewport dışına çıkan öğe, boş içerik, yüklenmemiş CSS, sızmış
Bootstrap mavisi, eksik ikon fontu. Üç genişlikte de **sıfır gerçek kusur**.

**Görsel kontrol yetmeyen yerler** — bunlar gerçek POST turuyla test edildi, çünkü alan adları
view'larda load-bearing: satın alma siparişi, satış siparişi, reçete (%100 oran doğrulayıcısı).

---

## 8. Geliştirme döngüsü

```bash
# Şablon / CSS / JS değişiklikleri anında yansır (şablon önbelleği kapalı,
# gunicorn --reload), AMA statikler toplanmalı:
docker compose exec web python manage.py collectstatic --noinput

# Çeviri değişince:
docker compose exec web python manage.py makemessages -l en --ignore=staticfiles
# …locale/en/LC_MESSAGES/django.po düzenle…
docker compose exec web python manage.py compilemessages

# Her değişiklikten sonra:
docker compose exec web python manage.py smoke
```

**Bilinmesi gereken iki tuzak:**

1. `collectstatic` atlanırsa NGINX 404 döner ve sayfa **sessizce stilsiz** açılır
   (nginx'te `try_files` var, ama `<link>` hatayı konsola yazmaz).
2. `web`'i `--force-recreate` ettiğinizde **`nginx`'i de yeniden başlatın**. `nginx.conf`'taki
   `upstream django { server web:8000; }` adresi yalnızca nginx başlarken çözülür; `web` yeni
   IP alınca nginx eskisine gitmeye devam eder → **502**.

---

## 9. Bilerek kapsam dışı

- **Pivot görünümü** — `line_items` ~2 boyutlu; altbilgili gruplu tablo %5 maliyetle %90'ını
  veriyor, analiz hikâyesini grafik görünümü karşılıyor.
- **Chatter mesaj kutusu** — salt okunur `AuditLog` akışı. Hiçbir şey yazmayan sahte bir
  kutu, hiç olmamasından kötüdür.
  **Dikkat:** log'lar çoğu zaman ALT kayda bağlıdır (satın almada `GoodsReceipt`'e, faturada
  `Payment`'a), bu yüzden `{% ui_chatter obj related=… %}` ilişkili nesneleri de sorgular —
  aksi halde panel boş görünür.
- **Kayıtlı aramalar (Favoriler)** — kolon basılır, devre dışı. Gerçeği yeni model +
  migration + CRUD ister.
- **Yazdırma stil sayfası.**
- **Eksik geçişler için `log_action` eklemek** — değerli ama *davranış* değişikliği, UI değil.

## 10. Doğrulanmamış olanlar

Dürüstlük için: **ekran okuyucuyla gerçek erişilebilirlik testi**, **klavyeyle uçtan uca
gezinme** ve **Chromium dışı tarayıcılar** denenmedi. Kanban sürükle-bırak fare ve simüle
dokunmayla test edildi, **gerçek bir dokunmatik cihazda denenmedi** — 250ms basılı tutma
eşiği gerçek parmakla fazla hassas gelirse ayarlanmalı.
