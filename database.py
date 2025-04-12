import os
from peewee import *
from peewee import PostgresqlDatabase, Model
from playhouse.db_url import connect
import datetime
from playhouse.postgres_ext import JSONField 



#ce que j'ai ajoutte  (les variables d'environnement)
db = PostgresqlDatabase(
    os.getenv("DB_NAME", "default_db"),
    user=os.getenv("DB_USER", "user"),
    password=os.getenv("DB_PASSWORD", "password"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 5432))
)
# Modèle de produit
class Product(Model):
    id = IntegerField(primary_key=True)
    name = CharField()
    description = TextField()
    price = DecimalField(max_digits=10, decimal_places=2)  #Utilisation de DecimalField pour éviter les erreurs d'arrondi
    weight = IntegerField()
    in_stock = BooleanField()
    image = CharField()
    type = CharField()
    height = IntegerField()

    class Meta:
        database = db  # Associe le modèle à la base de données

# Modèle de commande
class Order(Model):
    id = AutoField()
    #product = ForeignKeyField(Product, backref='orders', on_delete='CASCADE')  # Suppression en cascade si un produit est supprimé
    #quantity = IntegerField()
    total_price = DecimalField(max_digits=10, decimal_places=2)  #  DecimalField pour éviter les erreurs d'arrondi
    total_price_tax = DecimalField(max_digits=10, decimal_places=2, null=True)  #  Champ pour inclure les taxes
    shipping_price = DecimalField(max_digits=10, decimal_places=2, null=True)  #  Frais de livraison
    email = CharField(null=True)  # Peut etre vide au départ
    paid = BooleanField(default=False)  #etat du paiement
    transaction_id = CharField(null=True, unique=True)  #  Ajout du champ transaction_id pour le paiement
    shipping_information = TextField(null=True)  # Ajout de l'attribut manquant
    is_paying = BooleanField(default=False)

    credit_card = JSONField(null=True)  # Pour stocker les infos partiellement masquées de la carte
    transaction_error = JSONField(null=True)  # Pour stocker les erreurs retournées par le paiement


    created_at = DateTimeField(default=datetime.datetime.now)  #  Date de création de la commande
    updated_at = DateTimeField(default=datetime.datetime.now)  #  Date de mise à jour de la commande

    class Meta:
        database = db

#ce que j'ai ajoutte     
class OrderItem(Model):
    order = ForeignKeyField(Order, backref='items', on_delete='CASCADE')
    product = ForeignKeyField(Product, backref='order_items', on_delete='CASCADE')
    quantity = IntegerField()

    class Meta:
        database = db

# Création des tables
def initialize_db():
    from database import Product, Order, OrderItem
    db.connect()
    db.create_tables([Product, Order, OrderItem], safe=True)
    db.close()

if __name__ == "__main__":
    initialize_db()
    print("Base de données initialisée avec succès !")
