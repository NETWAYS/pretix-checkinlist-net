from django.apps import AppConfig
from django.utils.translation import ugettext_lazy


class PluginApp(AppConfig):
    name = 'pretix_checkinlist_net'
    verbose_name = 'Pretix Checkin List Exporter for NETWAYS'

    class PretixPluginMeta:
        name = ugettext_lazy('Pretix Checkin List Exporter for NETWAYS')
        author = 'NETWAYS GmbH'
        description = ugettext_lazy('Short description')
        visible = True
        version = '1.0.0'

    def ready(self):
        from . import signals  # NOQA


default_app_config = 'pretix_checkinlist_net.PluginApp'
