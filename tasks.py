import requests
from database import Order, Product, OrderItem, db
from decimal import Decimal
import os

PAYMENT_URL = "https://dimensweb.uqac.ca/~jgnault/shops/pay/"

def process_payment(order_id, credit_card):
    db.connect(reuse_if_open=True)

    print(f" Paiement en cours pour la commande {order_id}...")

    order = Order.get_or_none(Order.id == order_id)
    if not order:
        print(f"Commande {order_id} introuvable.")
        return

    amount = float(order.total_price_tax) + float(order.shipping_price)
    payment_data = {
        "credit_card": credit_card,
        "amount_charged": amount
    }

    try:
        response = requests.post(PAYMENT_URL, json=payment_data)

        if response.status_code == 422:
            print(f" Échec de paiement pour la commande {order_id}")
            order.transaction_error = response.json()["error"]
            order.paid = False
            order.is_paying = False
            order.save()
            return

        response.raise_for_status()

        payment_info = response.json()

        order.paid = True
        order.transaction_id = payment_info["transaction"]["id"]
        order.credit_card = {
            "name": payment_info["credit_card"]["name"],
            "first_digits": payment_info["credit_card"]["first_digits"],
            "last_digits": str(payment_info["credit_card"]["last_digits"]),
            "expiration_year": payment_info["credit_card"]["expiration_year"],
            "expiration_month": payment_info["credit_card"]["expiration_month"]
        }
        order.transaction_error = {}
        order.is_paying = False 
        order.save()

        print(f" Paiement réussi pour la commande {order_id}")

    except Exception as e:
        print(f" Erreur serveur pendant le paiement de la commande {order_id} : {e}")
        order.transaction_error = {
            "code": "server-error",
            "name": str(e)
        }
        order.paid = False
        order.is_paying = False  
        order.save()

    finally:
        db.close()
