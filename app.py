#PROJET DE SESSION 
#TECHNOLOGIES WEB AVANCEES
#REALISE PAR : MAMADOU CIRE BAH, IBRAHIM DIAKITE , ABOUBACAR DEMBA BAH, MARIAMA NDOUR SAGNE 

# Standard
import os
import json
import decimal
from decimal import Decimal

# Externes
import requests
import click
import redis
from flask import Flask, jsonify, request, send_from_directory
from flask.cli import AppGroup, with_appcontext
from redis import Redis
from rq import Worker, Queue
from rq.connections import Connection

from peewee import OperationalError

# Internes
from database import db, Product, Order, OrderItem, initialize_db
from cache import redis_client
from config import queue
from tasks import process_payment
import click
from flask.cli import with_appcontext


def clean_string(value):
    if isinstance(value, str):
        return value.replace('\x00', '')
    return value

app = Flask(__name__)


PAYMENT_URL = "https://dimensweb.uqac.ca/~jgnault/shops/pay/"

def register_routes(app):

    @app.route("/", methods=["GET"])
    def get_products():
        if Product.select().count() == 0:
            print("🔄Récupération des produits depuis le serveur distant...")
            response = requests.get("https://dimensweb.uqac.ca/~jgnault/shops/products/")
            
            if response.status_code == 200:
                try:
                    products_data = response.json()["products"]
                    for item in products_data:
                        Product.create(
                            id=item["id"],
                            name=clean_string(item["name"]),
                            description=clean_string(item["description"]),
                            price=item["price"],
                            weight=item["weight"],
                            in_stock=item["in_stock"],
                            image=clean_string(item["image"]),
                            type=clean_string(item["type"]),
                            height=item["height"]
                        )
                except Exception as e:
                    return jsonify({"error": f"Erreur de traitement des produits: {str(e)}"}), 500
            else:
                return jsonify({"error": "Erreur lors de la récupération des produits"}), 500

        products = Product.select()
        return jsonify({
            "products": [
                {
                    key: (float(value) if isinstance(value, Decimal) else value)
                    for key, value in product.__data__.items()
                }
                for product in products
            ]
        })


    # ce que j'ai modifie 
    @app.route("/order", methods=["POST"])
    def create_order():
        data = request.get_json()

        # rétrocompatibilité : accepter aussi "product"
        if "product" in data:
            products_data = [data["product"]]
        elif "products" in data:
            products_data = data["products"]
        else:
            return jsonify({"errors": {"products": {"code": "missing-fields", "name": "Liste de produits manquante"}}}), 422

        if not products_data:
            return jsonify({"errors": {"products": {"code": "missing-fields", "name": "Aucun produit fourni"}}}), 422

        total_price = 0
        total_weight = 0
        validated_products = []

        for item in products_data:
            if "id" not in item or "quantity" not in item:
                return jsonify({"errors": {"product": {"code": "missing-fields", "name": "Chaque produit doit avoir un id et une quantité"}}}), 422

            quantity = item["quantity"]
            if quantity < 1:
                return jsonify({"errors": {"product": {"code": "invalid-quantity", "name": "La quantité doit être ≥ 1"}}}), 422

            product = Product.get_or_none(Product.id == item["id"])
            if not product:
                return jsonify({"errors": {"product": {"code": "not-found", "name": f"Produit {item['id']} non trouvé"}}}), 404

            if not product.in_stock:
                return jsonify({"errors": {"product": {"code": "out-of-inventory", "name": f"Produit {item['id']} en rupture"}}}), 422

            validated_products.append((product, quantity))
            total_price += product.price * quantity
            total_weight += product.weight * quantity

        tax_rate = get_tax_rate("QC")
        shipping_price = calculate_shipping(total_weight)
        total_price_tax = total_price * tax_rate

        order = Order.create(
            total_price=total_price,
            total_price_tax=total_price_tax,
            shipping_price=shipping_price
        )

        for product, quantity in validated_products:
            OrderItem.create(order=order, product=product, quantity=quantity)

        return jsonify({"order_id": order.id}), 302

    @app.route("/order/<int:order_id>", methods=["GET"])
    def get_order(order_id):
        #  Etape 1 : Cherche dans Redis
        cached_order = redis_client.get(f"order:{order_id}")
        if cached_order:
            print(" Commande chargée depuis Redis")
            return jsonify(json.loads(cached_order)), 200

        #  etape 2  si pas dans Redis on tente Postgres (mais on capture l'erreur)
        try:
            order = Order.get_or_none(Order.id == order_id)
            if not order:
                return jsonify({"error": "Commande non trouvée"}), 404

            if order.is_paying:
                return '', 202

            # Parse infos de livraison
            try:
                shipping_information = json.loads(order.shipping_information) if order.shipping_information else {}
            except json.JSONDecodeError:
                shipping_information = {}

            # Construire transaction
            transaction = {}
            if order.paid:
                transaction = {
                    "id": order.transaction_id,
                    "success": True,
                    "amount_charged": float(order.total_price_tax) + float(order.shipping_price)
                }
            elif order.transaction_error:
                transaction = {
                    "success": False,
                    "error": order.transaction_error,
                    "amount_charged": float(order.total_price_tax) + float(order.shipping_price)
                }

            order_data = {
                "id": order.id,
                "total_price": float(order.total_price),
                "total_price_tax": float(order.total_price_tax),
                "shipping_price": float(order.shipping_price),
                "email": order.email,
                "credit_card": order.credit_card if order.paid else {},
                "shipping_information": shipping_information,
                "paid": order.paid,
                "transaction": transaction,
                "products": [
                    {
                        "id": item.product.id,
                        "quantity": item.quantity
                    } for item in order.items
                ]
            }

            #  Cache la commande dans Redis
            redis_client.set(f"order:{order_id}", json.dumps({"order": order_data}), ex=60)
            return jsonify({"order": order_data}), 200

        except OperationalError:
            return jsonify({"error": "Commande non disponible (base inaccessible)"}), 503


    @app.route("/order/<int:order_id>", methods=["PUT"])
    def update_or_pay_order(order_id):
        data = request.get_json()
        order = Order.get_or_none(Order.id == order_id)

        if not order:
            return jsonify({"error": "Commande non trouvée"}), 404

        has_credit_card = "credit_card" in data
        has_shipping_info_or_email = "order" in data and (
            "email" in data["order"] or "shipping_information" in data["order"]
        )

        if has_credit_card and has_shipping_info_or_email:
            return jsonify({
                "errors": {
                    "order": {
                        "code": "bad-request",
                        "name": "Vous ne pouvez pas fournir credit_card avec shipping_information et/ou email."
                    }
                }
            }), 400

        if "order" in data:
            order_data = data["order"]
            if "email" in order_data:
                order.email = order_data["email"]

            if "shipping_information" in order_data:
                shipping_info = order_data["shipping_information"]
                required_fields = ["country", "address", "postal_code", "city", "province"]

                if not all(field in shipping_info for field in required_fields):
                    return jsonify({
                        "errors": {
                            "order": {
                                "code": "missing-fields",
                                "name": "Il manque un ou plusieurs champs obligatoires."
                            }
                        }
                    }), 422

                order.shipping_information = json.dumps(shipping_info)
                tax_rate = get_tax_rate(shipping_info["province"])
                total_weight = sum(item.product.weight * item.quantity for item in order.items)
                order.shipping_price = calculate_shipping(total_weight)
                order.total_price_tax = (order.total_price + order.shipping_price) * tax_rate

            order.save()

        if has_credit_card:
            if order.paid:
                return jsonify({
                    "errors": {
                        "order": {
                            "code": "already-paid",
                            "name": "La commande a déjà été payée."
                        }
                    }
                }), 422

            if order.is_paying:
                return '', 409  # Paiement déjà en cours

            if not order.email or not order.shipping_information:
                return jsonify({
                    "errors": {
                        "order": {
                            "code": "missing-fields",
                            "name": "Les informations du client sont requises avant d'appliquer une carte de crédit."
                        }
                    }
                }), 422

            #  Marquer comme paiement en cours
            order.is_paying = True
            order.save()

            #  Mettre en file la tâche de paiement
            from tasks import process_payment
            from config import queue
            queue.enqueue(process_payment, order.id, data["credit_card"])

            return '', 202  # Paiement lancé en tâche de fond

        # Si aucune carte de crédit, on retourne la commande sans changement
        return jsonify({
            "order": {
                "id": order.id,
                "total_price": float(order.total_price),
                "total_price_tax": float(order.total_price_tax),
                "shipping_price": float(order.shipping_price),
                "email": order.email,
                "credit_card": order.credit_card if order.paid else {},
                "shipping_information": order.shipping_information,
                "paid": order.paid,
                "transaction": {} if not order.paid else {
                    "id": order.transaction_id,
                    "success": True,
                    "amount_charged": float(order.total_price_tax) + float(order.shipping_price)
                },
                "products": [
                    {
                        "id": item.product.id,
                        "quantity": item.quantity
                    } for item in order.items
                ]
            }
        }), 200


    @app.route("/order/<int:order_id>/shops/pay", methods=["POST"])
    def pay_order(order_id):
        data = request.get_json()
        order = Order.get_or_none(Order.id == order_id)

        if not order:
            return jsonify({"error": "Commande non trouvee"}), 404

        if order.paid:
            return jsonify({
                "errors": {
                    "order": {
                        "code": "already-paid",
                        "name": "La commande a deja ete payee."
                    }
                }
            }), 422

        if "credit_card" not in data:
            return jsonify({"error": "Donnees de paiement non fournies"}), 400

        if not order.email or not order.shipping_information:
            return jsonify({
                "errors": {
                    "order": {
                        "code": "missing-fields",
                        "name": "Les informations du client sont necessaires avant d'appliquer une carte de credit"
                    }
                }
            }), 422

        credit_card = data["credit_card"]
        payment_data = {
            "credit_card": credit_card,
            "amount_charged": float(order.total_price_tax) + float(order.shipping_price)
        }

        response = requests.post(PAYMENT_URL, json=payment_data)

        if response.status_code == 401:
            return jsonify({"error": "Acces refuse au service de paiement. Verifiez les permissions."}), 401

        if response.status_code == 422:
            return jsonify(response.json()), 422

        if response.status_code != 200:
            return jsonify({"error": "Service de paiement indisponible", "status_code": response.status_code}), 500

        try:
            payment_info = response.json()
        except requests.exceptions.JSONDecodeError:
            return jsonify({"error": "Réponse invalide du service de paiement"}), 500

        order.paid = True
        order.transaction_id = payment_info["transaction"]["id"]
        order.credit_card = {
            "name": payment_info["credit_card"]["name"],
            "first_digits": payment_info["credit_card"]["first_digits"],
            "last_digits": str(payment_info["credit_card"]["last_digits"]),
            "expiration_year": payment_info["credit_card"]["expiration_year"],
            "expiration_month": payment_info["credit_card"]["expiration_month"]
        }
        order.save()

        # Générer les données complètes de la commande
        order_data = {
            "id": order.id,
            "total_price": float(order.total_price),
            "total_price_tax": float(order.total_price_tax),
            "shipping_price": float(order.shipping_price),
            "email": order.email,
            "credit_card": order.credit_card,
            "shipping_information": order.shipping_information,
            "paid": order.paid,
            "transaction": payment_info["transaction"],
            "products": [
                {
                    "id": item.product.id,
                    "quantity": item.quantity
                } for item in order.items
            ]
        }

        #  Mettre en cache dans Redis pour assurer la résilience
        from cache import redis_client
        import json
        redis_client.set(f"order:{order.id}", json.dumps({"order": order_data}))

        #  Retourner la réponse complète au client
        return jsonify({"order": order_data}), 200


def get_tax_rate(province):
    tax_rates = {
        "QC": Decimal("1.15"),
        "ON": Decimal("1.13"),
        "AB": Decimal("1.05"),
        "BC": Decimal("1.12"),
        "NS": Decimal("1.14")
    }
    return tax_rates.get(province, Decimal("1.0"))

def calculate_shipping(weight):
    if weight <= 500:
        return 5
    elif weight <= 2000:
        return 10
    else:
        return 25


register_routes(app)
#initialize_db()
application = app

@app.route("/page/<path:filename>")
def html_pages(filename):
    return send_from_directory("pageWEB", filename)

@app.route("/style/<path:filename>")
def styles(filename):
    return send_from_directory("pageWEB/style", filename)


# --- Commande worker CLI ---
worker_cli = AppGroup("worker")

@worker_cli.command("run")
def run_worker():
    """Démarre un worker RQ qui écoute la queue 'default'."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_conn = Redis.from_url(redis_url)
    worker = Worker([queue], connection=redis_conn)
    worker.work()


# Ajoute la commande CLI personnalisée
app.cli.add_command(worker_cli)


@click.command("init-db")
@with_appcontext
def init_db_command():
    initialize_db()
    click.echo(" Base de données initialisée avec succès.")

app.cli.add_command(init_db_command)


# --- Main local ---
if __name__ == "__main__":
    app.run(debug=True)

