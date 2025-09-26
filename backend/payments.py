"""
Payment processing for GitHub-to-EXE Converter
Supports PayPal, Stripe, and Paystack (Mobile Money for Ghana)
"""
import os
import stripe
import paypalrestsdk
from flask import request, jsonify

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Configure PayPal
paypalrestsdk.configure({
    "mode": os.getenv('PAYPAL_MODE', 'sandbox'),  # sandbox or live
    "client_id": os.getenv('PAYPAL_CLIENT_ID'),
    "client_secret": os.getenv('PAYPAL_CLIENT_SECRET')
})

def create_stripe_payment(amount=7.00, currency='usd'):
    """Create Stripe payment session"""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': 'GitHub-to-EXE Hosting Support',
                        'description': 'Help upgrade to paid hosting for faster builds',
                    },
                    'unit_amount': int(amount * 100),  # Amount in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.host_url + 'success',
            cancel_url=request.host_url + 'cancel',
        )
        return {'success': True, 'checkout_url': session.url}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_paypal_payment(amount=7.00, currency='USD'):
    """Create PayPal payment"""
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": request.host_url + "success",
                "cancel_url": request.host_url + "cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "GitHub-to-EXE Hosting Support",
                        "sku": "hosting-support",
                        "price": str(amount),
                        "currency": currency,
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(amount),
                    "currency": currency
                },
                "description": "Help upgrade to paid hosting for faster builds"
            }]
        })

        if payment.create():
            # Get approval URL
            for link in payment.links:
                if link.rel == "approval_url":
                    return {'success': True, 'approval_url': link.href}
        else:
            return {'success': False, 'error': payment.error}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_paystack_payment(amount=50.00, currency='GHS', email='donor@example.com'):
    """Create Paystack payment for Mobile Money (Ghana)"""
    try:
        import requests

        headers = {
            'Authorization': f'Bearer {os.getenv("PAYSTACK_SECRET_KEY")}',
            'Content-Type': 'application/json'
        }

        data = {
            'email': email,
            'amount': int(amount * 100),  # Amount in pesewas
            'currency': currency,
            'callback_url': request.host_url + 'success',
            'metadata': {
                'purpose': 'GitHub-to-EXE Hosting Support'
            }
        }

        response = requests.post('https://api.paystack.co/transaction/initialize',
                               headers=headers, json=data)

        if response.status_code == 200:
            data = response.json()
            return {'success': True, 'authorization_url': data['data']['authorization_url']}
        else:
            return {'success': False, 'error': response.text}
    except Exception as e:
        return {'success': False, 'error': str(e)}