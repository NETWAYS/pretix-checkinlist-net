import logging

from collections import OrderedDict
from django import forms
from django.db.models import Max, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.translation import pgettext, ugettext as _, ugettext_lazy
from pretix.base.exporter import BaseExporter, ListExporter
from pretix.base.models import (
    Checkin, InvoiceAddress, Order, OrderPosition, Question,
)
from pretix.base.settings import PERSON_NAME_SCHEMES
from pretix.control.forms.widgets import Select2

logger = logging.getLogger(__name__)


class CheckInListMixin(BaseExporter):
    @property
    def _fields(self):
        name_scheme = PERSON_NAME_SCHEMES[self.event.settings.name_scheme]
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

        d['list'].queryset = self.event.checkin_lists.all()
        d['list'].widget = Select2(
            attrs={
                'data-model-select2': 'generic',
                'data-select2-url': reverse('control:event.orders.checkinlists.select2', kwargs={
                    'event': self.event.slug,
                    'organizer': self.event.organizer.slug,
                }),
                'data-placeholder': _('Check-in list')
            }
        )
        d['list'].widget.choices = d['list'].choices
        d['list'].required = True

        return d

    def _get_queryset(self, cl, form_data):
        cqs = Checkin.objects.filter(
            position_id=OuterRef('pk'),
            list_id=cl.pk
        ).order_by().values('position_id').annotate(
            m=Max('datetime')
        ).values('m')

        qs = OrderPosition.objects.filter(
            order__event=self.event,
        ).annotate(
            last_checked_in=Subquery(cqs)
        ).prefetch_related(
            'answers', 'answers__question', 'addon_to__answers', 'addon_to__answers__question'
        ).select_related('order', 'item', 'variation', 'addon_to', 'order__invoice_address', 'voucher')

        if not cl.all_products:
            qs = qs.filter(item__in=cl.limit_products.values_list('id', flat=True))

        if cl.subevent:
            qs = qs.filter(subevent=cl.subevent)

        # NET: Always sort by name; attribute change to `_cached`
        # with 2.1.0: https://github.com/pretix/pretix/issues/978
        qs = qs.order_by(Coalesce('attendee_name_cached', 'addon_to__attendee_name_cached'))

        # NET: Always include paid/non-paid
        qs = qs.filter(order__status__in=(Order.STATUS_PAID, Order.STATUS_PENDING))

        return qs

    def _get_dataset(self, qs, questions):
        # Collect and store data in preferred output format
        coll = {}
        collected_product_columns = []
        collected_question_columns = []

        for op in qs:
            try:
                ia = op.order.invoice_address
            except InvoiceAddress.DoesNotExist:
                ia = InvoiceAddress()

            order_code = op.order.code
            attendee = op.attendee_name or (op.addon_to.attendee_name if op.addon_to else '')
            product = str(op.item.name) + ((' - ' + str(op.variation.value)) if op.variation else '')
            paid = _('Yes') if op.order.status == Order.STATUS_PAID else _('No')
            email = op.attendee_email or (op.addon_to.attendee_email if op.addon_to else '')

            # Product will be added as new column
            if product not in collected_product_columns:
                collected_product_columns.append(product)

            # Check whether we need to modify an existing attendee
            new_row = {}
            if attendee in coll:
                new_row = coll[attendee]

            new_row['order_code'] = order_code

            # Attendee name parts
            name_scheme = PERSON_NAME_SCHEMES[self.event.settings.name_scheme]

            if len(name_scheme['fields']) > 1:
                attendee_name_parts = []
                for k, label, w in name_scheme['fields']:
                    attendee_name_parts.append((op.attendee_name_parts
                                                or (op.addon_to.attendee_name_parts
                                                    if op.addon_to else {}) or ia.name_parts).get(k, ''))

                new_row['attendee_name_parts'] = attendee_name_parts

            new_row['company'] = ia.company
            new_row['street'] = ia.street
            new_row['zipcode'] = ia.zipcode
            new_row['city'] = ia.city
            new_row['country'] = ia.country.name

            if not email:
                new_row['email'] = op.order.email
            else:
                new_row['email'] = email

            if op.voucher:
                new_row['voucher'] = op.voucher.code
            else:
                new_row['voucher'] = ''

            # Collect products
            if 'products' not in new_row:
                new_row['products'] = {}

            # Store the product
            # new_row['products'][product] = paid
            new_row['products'][product] = "yes"

            # Collect questions
            if 'questions' not in new_row:
                new_row['questions'] = {}

            acache = {}
            for answer in op.answers.all():
                acache[answer.question_id] = str(answer)

            for question in questions:
                question_str = str(question.question)  # cast from LazyI18nString

                # We are grouping ticket + addons here, and if not all three of them answer the question, just
                # take the first one which provides one.
                if question_str in new_row['questions'] and new_row['questions'][question_str] != '':
                    continue

                # Question will be added as new column
                if question_str not in collected_question_columns:
                    collected_question_columns.append(question_str)

                new_row['questions'][question_str] = acache.get(question.pk, '')

            # logger.error(new_row)

            # Pass back to collection
            coll[attendee] = new_row

            # logger.error(coll)

            # for loop end

        # return result set
        return coll, collected_product_columns, collected_question_columns


class CSVCheckinListNet(CheckInListMixin, ListExporter):
    name = "overview"
    identifier = 'checkinlistnet'
    verbose_name = ugettext_lazy('Check-in list for NETWAYS')

    @property
    def additional_form_fields(self):
        return self._fields

    def iterate_list(self, form_data):
        # Fetch data from checkin_list
        cl = self.event.checkin_lists.get(pk=form_data['list'])

        # Questions
        questions = list(Question.objects.filter(event=self.event, id__in=form_data['questions']))

        # Extract data from parent class helper
        qs = self._get_queryset(cl, form_data)

        # Collect the dataset in our custom format
        coll, collected_product_columns, collected_question_columns = self._get_dataset(qs, questions)

        # Start building the output
        columns = ['Order name', 'Attendee name', 'Company', 'Street', 'Zipcode', 'City', 'Country', 'Email', 'Voucher']

        # Add support for Attendee name parts
        name_scheme = PERSON_NAME_SCHEMES[self.event.settings.name_scheme]

        if len(name_scheme['fields']) > 1:
            for k, label, w in name_scheme['fields']:
                columns.append(_('Attendee name: {part}').format(part=label))

        # Header - order is important
        headers = columns + collected_product_columns + collected_question_columns
        yield headers

        # Body
        for attendee, data in coll.items():
            # , data['company'], data['street'], data['zipcode'], data['city'],
            # data['country'], data['email'], data['voucher']
            row = [data['order_code'], attendee,
                   data['company'],  data['street'], data['zipcode'], data['city'], data['country'],
                   data['email'], data['voucher']]

            # Attendee name parts
            if len(name_scheme['fields']) > 1:
                for n in data['attendee_name_parts']:
                    row.append(n)

            # Products as columns
            for c in collected_product_columns:
                if c in data['products']:
                    row.append(data['products'][c])
                else:
                    row.append('')  # empty value

            # logger.error(row['questions'])

            # Questions as columns
            for q in collected_question_columns:
                if q in data['questions']:
                    row.append(data['questions'][q])
                else:
                    row.append('')  # empty value

            # logger.error(row)

            # Write the row via ListExporter class
            yield row

        # for attendee, row in coll.items():

    def get_filename(self):
        return '{}_checkin_net'.format(self.event.slug)
