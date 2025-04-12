import requests
from database import Product, db

# URL de l'API externe
PRODUCTS_URL = "http://dimensweb.uqac.ca/~jgnault/shops/products/"

def fetch_and_store_products():
    """Récupère les produits depuis l'API distante et les stocke en base de données."""
    response = requests.get(PRODUCTS_URL)

    if response.status_code == 200:
        products_data = response.json()["products"]

        with db.atomic():  # Permet d'optimiser les insertions
            for product in products_data:
                existing_product = Product.get_or_none(Product.id == product["id"])
                if existing_product is None:
                    Product.create(
                        id=product["id"],
                        name=product["name"],
                        description=product["description"],
                        price=product["price"],
                        weight=product["weight"],
                        in_stock=product["in_stock"],
                        image=product["image"]
                    )
        print("Produits enregistrés avec succès !")
    else:
        print("Erreur lors de la récupération des produits:", response.status_code)

if __name__ == "__main__":
    db.connect()
    db.create_tables([Product])
    fetch_and_store_products()
    db.close()
