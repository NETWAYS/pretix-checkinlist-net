from django.apps import AppConfig
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy

from packaging import version

from pretix import __version__ as appVersion

class PluginApp(AppConfig):
    name = 'pretix_checkinlist_net'
    verbose_name = 'Pretix Checkin List Exporter for NETWAYS'
    required_core_version = '2.5.0'

    class PretixPluginMeta:
        name = ugettext_lazy('Pretix Checkin List Exporter for NETWAYS')
        author = 'NETWAYS GmbH'
        description = ugettext_lazy('This plugins allows to create custom event exports in Excel/CSV')
        visible = True
        version = '2.0.2'

    def ready(self):
        from . import signals  # NOQA

    @cached_property
    def compatibility_warnings(self):
        errs = []

        if version.parse(appVersion) < version.parse(self.required_core_version):
            errs.append("Pretix version %s is too old. Minimum required is %s." % (appVersion, self.required_core_version))

        return errs


default_app_config = 'pretix_checkinlist_net.PluginApp'
