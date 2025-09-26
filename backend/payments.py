"""
Payment processing for GitHub-to-EXE Converter
Supports PayPal, Stripe, and Paystack (Mobile Money for Ghana)
"""
import os
import math
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

def validate_payment_amount(amount):
    """Validate payment amount with comprehensive checks"""
    try:
        # Convert to float if it's a string
        if isinstance(amount, str):
            amount = float(amount)

        # Check for valid number
        if not isinstance(amount, (int, float)) or not amount or amount != amount:  # NaN check
            return None, "Amount must be a valid number"

        # Check for finite number
        if not math.isfinite(amount):
            return None, "Amount must be a finite number"

        # Check bounds
        MIN_AMOUNT = 0.5
        MAX_AMOUNT = 10000
        if amount < MIN_AMOUNT:
            return None, f"Amount must be at least ${MIN_AMOUNT}"
        if amount > MAX_AMOUNT:
            return None, f"Amount cannot exceed ${MAX_AMOUNT}"

        # Round to cents to avoid floating point issues
        validated_amount = round(amount * 100) / 100
        return validated_amount, None

    except (ValueError, TypeError) as e:
        return None, f"Invalid amount format: {str(e)}"

def create_stripe_payment(amount=7.00, currency='usd'):
    """Create Stripe payment session"""
    # Validate amount first
    validated_amount, error = validate_payment_amount(amount)
    if error:
        return {'success': False, 'error': error}

    # Check if Stripe is configured
    if not os.getenv('STRIPE_SECRET_KEY'):
        return {'success': False, 'error': 'Stripe not configured. Please set STRIPE_SECRET_KEY environment variable.'}

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
                    'unit_amount': int(validated_amount * 100),  # Amount in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=(request.host_url if request else "http://localhost:5000/") + 'success',
            cancel_url=(request.host_url if request else "http://localhost:5000/") + 'cancel',
        )
        return {'success': True, 'checkout_url': session.url}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_paypal_payment(amount=7.00, currency='USD'):
    """Create PayPal payment"""
    # Validate amount first
    validated_amount, error = validate_payment_amount(amount)
    if error:
        return {'success': False, 'error': error}

    # Check if PayPal is configured
    if not os.getenv('PAYPAL_CLIENT_ID') or not os.getenv('PAYPAL_CLIENT_SECRET'):
        return {'success': False, 'error': 'PayPal not configured. Please set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET environment variables.'}

    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": (request.host_url if request else "http://localhost:5000/") + "success",
                "cancel_url": (request.host_url if request else "http://localhost:5000/") + "cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "GitHub-to-EXE Hosting Support",
                        "sku": "hosting-support",
                        "price": str(validated_amount),
                        "currency": currency,
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(validated_amount),
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
            'callback_url': (request.host_url if request else "http://localhost:5000/") + 'success',
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