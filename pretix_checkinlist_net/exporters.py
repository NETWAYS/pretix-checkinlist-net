import io
import logging
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

logger = logging.getLogger(__name__)

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
                ('questions',
                 forms.ModelMultipleChoiceField(
                     queryset=self.event.questions.all(),
                     label=_('Include questions'),
                     widget=forms.CheckboxSelectMultiple(
                         attrs={'class': 'scrolling-multiple-choice'}
                     ),
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
        # Fetch data from checkin_list
        checkin_list = self.event.checkin_lists.get(pk=form_data['list'])

        qs = OrderPosition.objects.filter(
            order__event=self.event,
        ).prefetch_related(
            'answers', 'answers__question'
        ).select_related('order', 'item', 'variation', 'addon_to')

        if not checkin_list.all_products:
            qs = qs.filter(item__in=checkin_list.limit_products.values_list('id', flat=True))

        if checkin_list.subevent:
            qs = qs.filter(subevent=checkin_list.subevent)

        # NET: Always sort by name
        qs = qs.order_by(Coalesce('attendee_name', 'addon_to__attendee_name'))

        headers = [
            _('Order code'), _('Attendee name'), _('Product'), _('Price')
        ]

        # NET: Always include paid/non-paid
        qs = qs.filter(order__status__in=(Order.STATUS_PAID, Order.STATUS_PENDING))
        headers.append(_('Paid'))

        if self.event.settings.attendee_emails_asked:
            headers.append(_('E-mail'))

        if self.event.has_subevents:
            headers.append(pgettext('subevent', 'Date'))

        # Questions - TODO
        questions = list(Question.objects.filter(event=self.event, id__in=form_data['questions']))

        for question in questions:
            headers.append(str(question.question))

        # Collect and store data in preferred output format
        coll = {}
        collected_columns = []

        for op in qs:
            order_code = op.order.code
            attendee = op.attendee_name or (op.addon_to.attendee_name if op.addon_to else '')
            product = str(op.item.name) + (" – " + str(op.variation.value) if op.variation else "")
            paid = _('Yes') if op.order.status == Order.STATUS_PAID else _('No')
            email = op.attendee_email or (op.addon_to.attendee_email if op.addon_to else '')

            # Product will be added as new column
            if product not in collected_columns:
                collected_columns.append(product)

            # Check whether we need to modify an existing attendee
            new_row = {}
            if attendee in coll:
                new_row = coll[attendee]

            new_row['order_code'] = order_code

            # Initialize if there are no products yet
            if 'products' not in new_row:
                new_row['products'] = {}

            # Store the product
            #new_row['products'][product] = paid
            new_row['products'][product] = "yes"

            # Pass back to collection
            coll[attendee] = new_row

        # for loop end

        columns = [ 'Order name', 'Attendee name' ]

        # Append questions to columns - TODO

        # IO
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC, delimiter=",")

        # Header
        headers = columns + collected_columns
        writer.writerow(headers)

        # Body
        for attendee, row in coll.items():
            line = []
            line.append(row['order_code'])
            line.append(attendee)

            for c in collected_columns:
                if c in row['products']:
                    line.append(row['products'][c])
                else:
                    line.append('') # empty value

            # Store the line
            new_row = line

            # Write the row
            writer.writerow(new_row)

        # for attendee, row in coll.items():

        # Dump file
        return 'checkin_net.csv', 'text/csv', output.getvalue().encode("utf-8")
