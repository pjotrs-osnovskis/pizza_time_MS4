# Followed Code Institute's Boutique Ado guidance.

from django.http import HttpResponse
from .models import CheckoutOrder, CheckoutLineItem
from products.models import Product
from profiles.models import UserProfile

import json
import time

class StripWebHookHandler:
    """ Handle Stripe Webhooks"""

    def __init__(self, request):
        self.request = request

    def handle_event(self, event):
        """
        Handle a generic/unknown/unexpected webhook event
        """
        return HttpResponse(
            content=f'Webhook received: {event["type"]}',
            status=200)
    
    def handle_payment_intent_succeeded(self, event):
        """
        Handle the payment_intent.succeeded webhook from Stripe
        """
        intent = event.data.object
        pid = intent.id
        order = intent.metadata.order
        save_info = intent.metadata.save_info

        billing_details = intent.charges.data[0].billing_details
        shipping_details = intent.shipping
        grand_total = round(intent.data.charges[0].amount / 100, 2)

        # Remove Address field if empty, i.e. street_address2
        for field, value in shipping_details.address.items():
            if value == '':
                shipping_details.address[field] = None

        # Update information when save_info was checked
        profile = None
        username = intent.metadata.username
        if username != 'AnonymousUser':
            profile = UserProfile.objects.get(user__username=username)
            if save_info:
                profile.f_name = shipping_details.f_name
                profile.l_name = shipping_details.l_name
                profile.default_phone_number = shipping_details.phone
                profile.default_postcode = shipping_details.address.postal_code
                profile.default_city = shipping_details.address.city
                profile.default_street_address1 = shipping_details.address.line1
                profile.default_street_address2 = shipping_details.address.line2
                profile.save()

        order_exists = False
        attempt = 1
        while attempt <= 5:
            try:
                single_order = CheckoutOrder.object.get(
                    f_name__iexact = shipping_details.f_name,
                    l_name__iexact = shipping_details.l_name,
                    email__iexact = billing_details.email,
                    phone_number__iexact = shipping_details.phone_number,
                    street_address1__iexact = shipping_details.address.line1,
                    street_address2__iexact = shipping_details.address.line2,
                    city__iexact = shipping_details.address.city,
                    postcode__iexact = shipping_details.address.postal_code,
                    grand_total__iexact = grand_total,
                    original_order = order,
                    stripe_pid = pid,
                )

                order_exists = True
                break

            except CheckoutOrder.DoesNotExist:
                attempt += 1
                time.sleep(1)

        if order_exists:
            return HttpResponse(
                content=f'Webhook received: {event["type"]} | SUCCESS: Verified order is already in database.',
                status=200)

        else:
            single_order = None
            try:
                single_order = CheckoutOrder.objects.create(
                    f_name__iexact = shipping_details.f_name,
                    l_name__iexact = shipping_details.l_name,
                    user_profile = profile,
                    email = billing_details.email,
                    phone_number = shipping_details.phone_number,
                    street_address1 = shipping_details.address.line1,
                    street_address2__iexact = shipping_details.address.line2,
                    city = shipping_details.address.city,
                    postcode = shipping_details.address.postal_code,
                    grand_total = grand_total,
                    original_order = order,
                    stripe_pid = pid,

                )
                for item_id, item_data in json.loads(order).items():
                    product = Product.objects.get(pk=item_id)
                    if isinstance(item_data, int):
                        checkout_line_item = CheckoutLineItem(
                            order=order,
                            product=product,
                            qty=item_data,
                        )
                        checkout_line_item.save()
                    else:
                        for size, qty in item_data['items_by_size'].items():
                            checkout_line_item = CheckoutLineItem(
                                order=order,
                                qty = qty,
                                size = size,
                                product = product,
                            )
                            checkout_line_item.save()

            except Exception as e:
                if single_order:
                    single_order.delete()
                return HttpResponse(
                    content=f'Webhook received: {event["type"]} | ERROR: {e}',
                    status=500)

        return HttpResponse(
            content=f'Webhook received: {event["type"]} | SUCCESS: Order created in webhook.',
            status=200)

    def handle_payment_intent_payment_failed(self, event):
        """
        Handle the payment_intent.payment_failed webhook from Stripe
        """
        return HttpResponse(
            content=f'Webhook received: {event["type"]}',
            status=200)