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
                ('secrets',
                 forms.BooleanField(
                     label=_('Include QR-code secret'),
                     required=False
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
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC, delimiter=",")
        cl = self.event.checkin_lists.get(pk=form_data['list'])

        questions = list(Question.objects.filter(event=self.event, id__in=form_data['questions']))
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
            _('Order code'), _('Attendee name'), _('Product'), _('Price')
        ]
        if form_data['paid_only']:
            qs = qs.filter(order__status=Order.STATUS_PAID)
        else:
            qs = qs.filter(order__status__in=(Order.STATUS_PAID, Order.STATUS_PENDING))
            headers.append(_('Paid'))

        if form_data['secrets']:
            headers.append(_('Secret'))

        if self.event.settings.attendee_emails_asked:
            headers.append(_('E-mail'))

        if self.event.has_subevents:
            headers.append(pgettext('subevent', 'Date'))

        for q in questions:
            headers.append(str(q.question))

        writer.writerow(headers)

        for op in qs:
            row = [
                op.order.code,
                op.attendee_name or (op.addon_to.attendee_name if op.addon_to else ''),
                str(op.item.name) + (" – " + str(op.variation.value) if op.variation else ""),
                op.price,
            ]
            if not form_data['paid_only']:
                row.append(_('Yes') if op.order.status == Order.STATUS_PAID else _('No'))
            if form_data['secrets']:
                row.append(op.secret)
            if self.event.settings.attendee_emails_asked:
                row.append(op.attendee_email or (op.addon_to.attendee_email if op.addon_to else ''))
            if self.event.has_subevents:
                row.append(str(op.subevent))
            acache = {}
            for a in op.answers.all():
                acache[a.question_id] = str(a)
            for q in questions:
                row.append(acache.get(q.pk, ''))

            writer.writerow(row)

        # NET specific
        # Hook into the output csv cache and change the layout
        # Ugly and not performant, but better portability on future changes
        output = self.render_combined(output.getvalue())

        return 'checkin_net.csv', 'text/csv', output.getvalue().encode("utf-8")

    def quote (self, string):
        return '"' + string + '"'

    def render_combined(self, csv_input):
        new_csv_output = io.StringIO();
        writer = csv.writer(new_csv_output, quoting=csv.QUOTE_NONNUMERIC, delimiter=",")

        #logger.exception(csv_input)

        # read input, use DictReader for proper access
        f = io.StringIO(csv_input)
        reader = csv.DictReader(f, quoting=csv.QUOTE_NONNUMERIC, delimiter=",")

        coll = {}
        columns = [ 'Order name', 'Attendee name' ]
        collected_columns = []

        for row in reader:
            #logger.exception(row)

            order_code = row['Order code']
            attendee = row['Attendee name']
            product = row['Product']

            # this is optional above, not always set
            try:
                paid = row['Paid']
            except KeyError:
                paid = ''

            # Product will be our new column header name
            if product not in collected_columns:
                collected_columns.append(product)

            # Check whether we need to modify an existing attendee
            new_row = {}
            if attendee in coll:
                new_row = coll[attendee]

            new_row['order_code'] = order_code

            # initialize if there are not products yet
            if 'products' not in new_row:
                new_row['products'] = {}

            #new_row['products'][product] = "Paid: " + paid # don't store true/false, if this field is set with the paid status, it will be printed
            new_row['products'][product] = "yes" # hide payment details from externals

            coll[attendee] = new_row
        # for row in reader:

        #headers = ';'.join(quote(x) for x in columns + collected_columns)
        headers = columns + collected_columns

        #print(header)
        writer.writerow(headers)

        #print("Collected Columns: ")
        #print(collected_columns)

        for attendee, row in coll.items():
            line = []
            line.append(row['order_code'])
            line.append(attendee)

            #print(row)

            for c in collected_columns:
                if c in row['products']:
                    line.append(row['products'][c])
                else:
                    line.append('') # empty value

            #new_row = ','.join(quote(x) for x in line)
            new_row = line

            #print(new_row)
            writer.writerow(new_row)
        # for attendee, row in coll.items():

        # return the same stringIO value
        return new_csv_output
