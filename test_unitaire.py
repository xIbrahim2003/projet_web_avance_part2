# PROJET DE SESSION 
# TECHNOLOGIES WEB AVANCEES 
# FICHIER DE TEST UNITAIRES
# REALISE PAR : IBRAHIM DIAKITE , ABOUBACAR DEMBA BAH, MARIAMA NDOUR SAGNE , MAMADOU CIRE BAH

import unittest
from flask import Flask
from app import app, get_tax_rate, calculate_shipping, Decimal
from database import Product, Order, initialize_db

class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialiser l'application Flask et la base de données
        app.config['TESTING'] = True
        cls.client = app.test_client()
        with app.app_context():
            initialize_db()  # Initialiser la base de données pour les tests

    def setUp(self):
        # Vérifier que le produit avec l'id 1 existe
        self.product_id = 1
        self.product = Product.get_or_none(Product.id == self.product_id)
        if not self.product:
            self.fail(f"Le produit avec l'id {self.product_id} n'existe pas dans la base de données.")

    # Test pour la route GET /, afin d'avoir la liste des produits
    def test_get_products(self):
        print("\nTEST DE LA ROUTE GET POUR RÉCUPÉRER LES PRODUITS...")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)  # Attendu : 200 OK

        # Vérifier que le produit existant est dans la réponse
        data = response.get_json()
        self.assertIn("products", data)
        self.assertTrue(any(product["id"] == self.product_id for product in data["products"]))
        print("SUCCÈS : Liste des produits récupérée avec succès!")

    def test_create_order_product_not_found(self):
        print("\nTEST DE LA CRÉATION D'UNE COMMANDE AVEC PRODUIT INEXISTANT...")
        # Tester la création d'une commande avec un produit inexistant
        response = self.client.post("/order", json={"product": {"id": 9999, "quantity": 1}})
        self.assertEqual(response.status_code, 404)  # Attendu : 404 Not Found
        error_data = response.get_json()
        self.assertIn("errors", error_data)
        self.assertEqual(error_data["errors"]["product"]["code"], "not-found")
        print("SUCCÈS : La commande avec produit inexistant a été correctement gérée!")


    # Test pour la création d'une commande valide
    def test_create_order_valid(self):
        print("\nTEST DE LA CREATION D'UNE COMMANDE VALIDE...")
        response = self.client.post("/order", json={"product": {"id": self.product_id, "quantity": 1}})
        self.assertEqual(response.status_code, 302)  # Attendu : 302 Found

        # Vérifier que la commande a été créée
        order_data = response.get_json()
        self.assertIn("order_id", order_data)
        print("SUCCES: Commande créée avec succès.")

    # Test pour la création d'une commande avec une quantité invalide
    def test_create_order_invalid_quantity(self):
        print("\nTEST DE LA CREATION D'UNE COMMANDE AVEC UNE QUANTITE INVALIDE...")
        response = self.client.post("/order", json={"product": {"id": self.product_id, "quantity": 0}})
        self.assertEqual(response.status_code, 422)  # Attendu : 422 Unprocessable Entity

        # Vérifier le message d'erreur
        error_data = response.get_json()
        self.assertIn("errors", error_data)
        self.assertEqual(error_data["errors"]["product"]["code"], "missing-fields")
        print("SUCCES: Quantité invalide, réponse correcte!")

    # Test pour la récupération d'une commande
    def test_get_order(self):
        print("\nTEST DE LA RECUPERATION D'UNE COMMANDE...")
        # Créer une commande de test
        response = self.client.post("/order", json={"product": {"id": self.product_id, "quantity": 1}})
        self.assertEqual(response.status_code, 302)  # Attendu : 302 Found

        # Récupérer l'ID de la commande créée
        order_id = response.get_json()["order_id"]

        # Tester la récupération de la commande
        response = self.client.get(f"/order/{order_id}")
        self.assertEqual(response.status_code, 200)  # Attendu : 200 OK

        # Vérifier les détails de la commande
        order_data = response.get_json()
        self.assertIn("order", order_data)
        self.assertEqual(order_data["order"]["product"]["id"], self.product_id)
        print("SUCCES: Commande récupérée avec succès!")

    # Test pour la mise à jour des informations de livraison
    def test_update_order_shipping_info(self):
        print("\nTEST DE LA MISE A JOUR DES INFORMATIONS DE LIVRAISON...")
        # Créer une commande de test
        response = self.client.post("/order", json={"product": {"id": self.product_id, "quantity": 1}})
        self.assertEqual(response.status_code, 302)  # Attendu : 302 Found

        # Récupérer l'ID de la commande créée
        order_id = response.get_json()["order_id"]

        # Mettre à jour les informations de livraison
        response = self.client.put(
            f"/order/{order_id}",
            json={
                "order": {
                    "email": "test@example.com",
                    "shipping_information": {
                        "country": "Canada",
                        "address": "123 Test Street",
                        "postal_code": "A1B 2C3",
                        "city": "Test City",
                        "province": "QC"
                    }
                }
            }
        )
        self.assertEqual(response.status_code, 200)  # Attendu : 200 OK

        # Vérifier que les informations ont été mises à jour
        order_data = response.get_json()
        self.assertEqual(order_data["order"]["email"], "test@example.com")
        self.assertEqual(order_data["order"]["shipping_information"]["city"], "Test City")
        print("SUCCES: Informations de livraison mises à jour !")

    # Test pour le paiement d'une commande via PUT /order/order_id
    def test_pay_order_put(self):
        print("\nTEST DE PAIEMENT D'UNE COMMANDE VIA PUT...")
        # Créer une commande de test
        response = self.client.post("/order", json={"product": {"id": self.product_id, "quantity": 1}})
        self.assertEqual(response.status_code, 302)  # Attendu : 302 Found

        # Récupérer l'ID de la commande créée
        order_id = response.get_json()["order_id"]

        # Ajouter des informations client à la commande
        response = self.client.put(
            f"/order/{order_id}",
            json={
                "order": {
                    "email": "test@example.com",
                    "shipping_information": {
                        "country": "Canada",
                        "address": "123 Test Street",
                        "postal_code": "A1B 2C3",
                        "city": "Test City",
                        "province": "QC"
                    }
                }
            }
        )
        self.assertEqual(response.status_code, 200)  # Attendu : 200 OK

        # Tester le paiement de la commande avec PUT /order/order id
        response = self.client.put(
            f"/order/{order_id}",
            json={
                "credit_card": {
                    "name": "John Doe",
                    "number": "4242 4242 4242 4242",  # Carte valide
                    "expiration_year": 2026,
                    "cvv": "123",
                    "expiration_month": 9
                }
            }
        )
        self.assertEqual(response.status_code, 200)  # Attendu : 200 OK

        # Vérifier que la commande est marquée comme payée
        order_data = response.get_json()
        self.assertIn("order", order_data)  # Vérifier que la clé "order" existe
        self.assertIn("paid", order_data["order"])  # Vérifier que la clé "paid" existe
        self.assertTrue(order_data["order"]["paid"])  # Vérifier que la commande est payée

        # Vérifier les détails de la transaction
        self.assertIn("transaction", order_data["order"])
        self.assertIn("credit_card", order_data["order"])
        print("SUCCES: Paiement de la commande effectué avec succès!")

    # Test pour le paiement d'une commande via POST /order/order_id/shops/pay
    def test_pay_order_post_shops_pay(self):
        print("\nTEST DE PAIEMENT D'UNE COMMANDE VIA POST /shops/pay ...")
        # Créer une commande de test
        response = self.client.post("/order", json={"product": {"id": self.product_id, "quantity": 1}})
        self.assertEqual(response.status_code, 302)  # Attendu : 302 Found

        # Récupérer l'ID de la commande créée
        order_id = response.get_json()["order_id"]

        # Ajouter des informations client à la commande
        response = self.client.put(
            f"/order/{order_id}",
            json={
                "order": {
                    "email": "test@example.com",
                    "shipping_information": {
                        "country": "Canada",
                        "address": "123 Test Street",
                        "postal_code": "A1B 2C3",
                        "city": "Test City",
                        "province": "QC"
                    }
                }
            }
        )
        self.assertEqual(response.status_code, 200)  # Attendu : 200 OK

        # Tester le paiement de la commande avec POST /order/order_id/shops/pay
        response = self.client.post(
            f"/order/{order_id}/shops/pay",
            json={
                "credit_card": {
                    "name": "John Doe",
                    "number": "4242 4242 4242 4242",  # Carte valide
                    "expiration_year": 2026,
                    "cvv": "123",
                    "expiration_month": 9
                }
            }
        )
        self.assertEqual(response.status_code, 200)  # Attendu : 200 OK

        # Vérifier que la commande est marquée comme payée
        order_data = response.get_json()
               
        # Vérifier les détails de la transaction si on voit success c'est que la transaction est réussie donc la commande a été payée
        self.assertIn("transaction", order_data["order"])
        self.assertEqual(order_data["order"]["transaction"]["success"], 'true')  # Vérifier que "success" est True
        print("SUCCES: Paiement de la commande effectué avec succès!")

    # Test pour la fonction get_tax_rate
    def test_get_tax_rate(self):
        print("\nTEST DE LA FONCTION GET_TAX_RATE ...")
        self.assertEqual(get_tax_rate("QC"), Decimal('1.15'))  # Québec
        self.assertEqual(get_tax_rate("ON"), Decimal('1.13'))  # Ontario
        self.assertEqual(get_tax_rate("AB"), Decimal('1.05'))  # Alberta
        self.assertEqual(get_tax_rate("BC"), Decimal('1.12'))  # Colombie-Britannique
        self.assertEqual(get_tax_rate("NS"), Decimal('1.14'))  # Nouvelle-Écosse
        self.assertEqual(get_tax_rate("XX"), Decimal('1.0'))  # Province inconnue
        print("SUCCES !")

    # Test pour la fonction calculate_shipping
    def test_calculate_shipping(self):
        print("\nTEST DE LA FONCTION CALCULATE_SHIPPING ...")
        self.assertEqual(calculate_shipping(400), 5)  # Moins de 500g
        self.assertEqual(calculate_shipping(600), 10)  # Entre 500g et 2000g
        self.assertEqual(calculate_shipping(2100), 25)  # Plus de 2000g
        self.assertEqual(calculate_shipping(2500), 25)  # Plus de 2000g
        print("SUCCES!")

    def test_update_order_missing_shipping_info(self):
        print("\nTEST DE LA MISE A JOUR D'UNE COMMANDE AVEC DES INFORMATIONS DE LIVRAISON MANQUANTES...")
        # Créer une commande de test
        response = self.client.post("/order", json={"product": {"id": self.product_id, "quantity": 1}})
        self.assertEqual(response.status_code, 302)  # Attendu : 302 Found

        # Récupérer l'ID de la commande créée
        order_id = response.get_json()["order_id"]

        # Tester la mise à jour avec des informations de livraison manquantes
        response = self.client.put(
            f"/order/{order_id}",
            json={
                "order": {
                    "email": "test@example.com",
                    "shipping_information": {
                        "country": "Canada",
                        "address": "123 Test Street",
                        # "postal_code" et "city" manquants
                    }
                }
            }
        )
        self.assertEqual(response.status_code, 422)  # Attendu : 422 Unprocessable Entity
        error_data = response.get_json()
        self.assertIn("errors", error_data)
        self.assertEqual(error_data["errors"]["order"]["code"], "missing-fields")
        print("SUCCES: Réponse correcte avec les erreurs attendues pour informations de livraison manquantes!")

    def tearDown(self):
        # Supprimer toutes les commandes créées pendant les tests
        with app.app_context():
            Order.delete().execute()
            
if __name__ == "__main__":
    unittest.main()