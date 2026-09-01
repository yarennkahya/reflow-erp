"""
Navigasyon registry'sindeki her rotayı her rolle GET eder.

Projede test paketi yok (*/tests.py boş). Bu komut, tasarım yeniden yazımının
ürettiği iki hata sınıfını yakalar:
  1) registry'de bayat bir url_name -> NoReverseMatch
  2) bir şablonun ihtiyaç duyduğu context değişkeninin kaybolması -> 500

Kullanım:
    python manage.py smoke
    python manage.py smoke --user root
    python manage.py smoke --fail-fast
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import NoReverseMatch, reverse

from dashboard.navigation import APPS

# Yan etkisi olan POST-only rotalar buradan atlanır; GET'leri 405 döner.
POST_ONLY = {
    'warehouse-activity', 'warehouse-delete',
    'purchase-order-advance', 'purchase-order-cancel', 'purchase-order-delete',
    'purchase-order-item-delete', 'purchase-order-item-receive',
    'supplier-activity', 'supplier-delete', 'supplier-product-delete',
    'return-approve', 'return-reject', 'return-request-create',
    'crm-customer-activity', 'crm-customer-delete', 'crm-sale-delete',
    'opportunity-advance', 'opportunity-lose', 'crm-sale-activity',
    'leave-approve', 'leave-reject', 'application-advance', 'application-reject',
    'opportunity-set-stage', 'order-set-status', 'purchase-order-set-status',
    'application-set-stage', 'employee-set-status',
    'meeting-cancel', 'invoice-create', 'invoice-send', 'ai-chat',
}

# Argüman gerektiren rotalar için örnek pk. Kayıt yoksa 404 beklenir, bu da
# şablon hatası olmadığını gösterir.
SAMPLE_PK = 1


class Command(BaseCommand):
    help = 'Registry rotalarını tüm demo rolleriyle dolaşır ve durum kodlarını doğrular.'

    def add_arguments(self, parser):
        parser.add_argument('--user', action='append', dest='users',
                            help='Yalnızca bu kullanıcı(lar) ile çalıştır.')
        parser.add_argument('--fail-fast', action='store_true',
                            help='İlk hatada dur.')

    def handle(self, *args, **options):
        # Test istemcisi 'testserver' host'uyla istek atar; ALLOWED_HOSTS'ta
        # olmadığı için her yanıt 400 dönerdi.
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

        User = get_user_model()
        names = options.get('users') or [
            'root', 'ik_kullanici', 'satis_kullanici',
            'satinalma_kullanici', 'uretim_kullanici',
        ]
        users = []
        for name in names:
            user = User.objects.filter(username=name).first()
            if user is None:
                self.stdout.write(self.style.WARNING(
                    f'  atlandı: {name} kullanıcısı yok '
                    f'(python manage.py setup_rbac ile oluşturulur)'))
                continue
            users.append(user)

        if not users:
            self.stderr.write(self.style.ERROR(
                'Hiç kullanıcı bulunamadı. Önce: python manage.py setup_rbac'))
            return

        template_issues = self._check_templates()
        if template_issues:
            self.stdout.write(self.style.ERROR('\nŞablon sorunları:'))
            for path, issue in template_issues:
                self.stdout.write(self.style.ERROR(f'  {path}: {issue}'))

        routes = []
        for app in APPS:
            for menu in app.menus:
                for route in menu.routes:
                    if route not in POST_ONLY:
                        routes.append((app.key, route))

        failures = []
        checked = 0

        for user in users:
            client = Client()
            client.force_login(user)
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n{user.username}'))

            for app_key, route in routes:
                url = self._reverse(route)
                if url is None:
                    failures.append((user.username, route, 'NoReverseMatch'))
                    self.stdout.write(self.style.ERROR(f'  ✗ {route}: reverse edilemedi'))
                    if options['fail_fast']:
                        return self._report(failures, checked)
                    continue

                try:
                    response = client.get(url)
                    status = response.status_code
                except Exception as exc:                     # noqa: BLE001
                    failures.append((user.username, route, f'{type(exc).__name__}: {exc}'))
                    self.stdout.write(self.style.ERROR(f'  ✗ {route}: {type(exc).__name__}: {exc}'))
                    if options['fail_fast']:
                        return self._report(failures, checked)
                    continue

                checked += 1
                if status in (200, 302, 404):
                    self.stdout.write(f'  · {route} [{status}]')
                else:
                    failures.append((user.username, route, f'HTTP {status}'))
                    self.stdout.write(self.style.ERROR(f'  ✗ {route}: HTTP {status}'))
                    if options['fail_fast']:
                        return self._report(failures, checked)

        self._report(failures, checked)

    @staticmethod
    def _check_templates():
        """
        Şablonlarda sessizce ekrana basılan hataları yakalar.

        Django'da {# ... #} YALNIZCA tek satırlıktır; çok satırlısı yorum
        sayılmaz ve olduğu gibi sayfaya yazılır. Ayrıca yeniden yazım
        sonrasında hiçbir şablonda inline <style> kalmamalı.
        """
        import re

        from django.conf import settings

        issues = []
        root = settings.BASE_DIR / 'templates'
        for path in sorted(root.rglob('*.html')):
            text = path.read_text(encoding='utf-8')
            rel = path.relative_to(settings.BASE_DIR)

            for match in re.finditer(r'\{#((?:(?!#\}).)*?)\n', text, re.S):
                issues.append((rel, 'çok satırlı {# #} yorumu — {% comment %} kullanın'))
                break

            if '<style' in text:
                issues.append((rel, 'inline <style> — CSS tasarım sistemine taşınmalı'))
        return issues

    @staticmethod
    def _reverse(route):
        # Bazı rotalar iki argüman alır (ör. purchase-order-item-edit:
        # <pk> + <item_pk>), bu yüzden 0/1/2 argümanla sırayla denenir.
        for args in ((), (SAMPLE_PK,), (SAMPLE_PK, SAMPLE_PK)):
            try:
                return reverse(route, args=args)
            except NoReverseMatch:
                continue
        return None

    def _report(self, failures, checked):
        self.stdout.write('')
        if failures:
            self.stdout.write(self.style.ERROR(
                f'{len(failures)} hata / {checked} istek'))
            for username, route, reason in failures:
                self.stdout.write(self.style.ERROR(f'  {username}  {route}  {reason}'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Tüm rotalar geçti ({checked} istek).'))
