import io
from collections import OrderedDict

from defusedcsv import csv
from django import forms
from django.db.models import Max, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils.formats import localize
from django.utils.translation import pgettext, ugettext as _, ugettext_lazy
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle

from pretix.base.exporter import BaseExporter
from pretix.base.models import Checkin, Order, OrderPosition, Question
from pretix.plugins.reports.exporters import ReportlabExportMixin

class BaseCheckinList(BaseExporter):
    @property
    def export_form_fields(self):
        d = OrderedDict(
            [
                ('list',
                 forms.ModelChoiceField(
                     queryset=self.event.checkin_lists.all(),
                     label=_('Check-in list'),
                     widget=forms.RadioSelect(
                         attrs={'class': 'scrolling-choice'}
                     ),
                     initial=self.event.checkin_lists.first()
                 )),
                ('paid_only',
                 forms.BooleanField(
                     label=_('Only paid orders'),
                     initial=True,
                     required=False
                 )),
                ('sort',
                 forms.ChoiceField(
                     label=_('Sort by'),
                     initial='name',
                     choices=(
                         ('name', _('Attendee name')),
                         ('code', _('Order code')),
                     ),
                     widget=forms.RadioSelect,
                     required=False
                 )),
            ]
        )
        return d


class CSVCheckinListNet(BaseCheckinList):
    name = "overview"
    identifier = 'checkinlistcsvnet'
    verbose_name = ugettext_lazy('Check-in list (CSV) for NETWAYS')

    def render(self, form_data: dict):
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC, delimiter=",")
        cl = self.event.checkin_lists.get(pk=form_data['list'])

        qs = OrderPosition.objects.filter(
            order__event=self.event,
        ).prefetch_related(
            'answers', 'answers__question'
        ).select_related('order', 'item', 'variation', 'addon_to')

        if not cl.all_products:
            qs = qs.filter(item__in=cl.limit_products.values_list('id', flat=True))

        if cl.subevent:
            qs = qs.filter(subevent=cl.subevent)

        if form_data['sort'] == 'name':
            qs = qs.order_by(Coalesce('attendee_name', 'addon_to__attendee_name'))
        elif form_data['sort'] == 'code':
            qs = qs.order_by('order__code')

        headers = [
            _('Order code'), _('Attendee name'), _('E-Mail')
        ]
        if form_data['paid_only']:
            qs = qs.filter(order__status=Order.STATUS_PAID)
        else:
            qs = qs.filter(order__status__in=(Order.STATUS_PAID, Order.STATUS_PENDING))

        collected_op = {}

        for op in qs:
            order_code = op.order.code

            if order_code in collected_op:
                collected_op[order_code].append(op)
            else:
                collected_op[order_code] = [ op ]

        # we need to know about the column count we will render later on.
        products = []
        datalist = []

        for order_code, ops in collected_op.items():
            data = {}
            data['products'] = {}
            data['order_code'] = order_code

            for op in ops:
                data['attendee_name'] = op.attendee_name or (op.addon_to.attendee_name if op.addon_to else '')
                data['email'] = op.attendee_email or (op.addon_to.attendee_email if op.addon_to else '')

                item_name = str(op.item.name) + (" – " + str(op.variation.value) if op.variation else "")

                # update global header columns
                if item_name not in products:
                    products.append(item_name)

                data['products'][item_name] = (1 if op.order.status == Order.STATUS_PAID else 0);

            datalist.append(data)

        products.remove('Ticket')

        products.sort()

        products[:0] = [ 'Ticket' ]

        for product in products:
            headers.append(product)

        writer.writerow(headers)

        for data in datalist:
            row = []
            row.append(data['order_code'])
            row.append(data['attendee_name'])
            row.append(data['email'])

            products = data['products']
            for item, val in products.items():
                row.append(val)

            writer.writerow(row)

        return 'checkin_net.csv', 'text/csv', output.getvalue().encode("utf-8")


