README - Projet de session 
Cours : Technologies Web Avancées
Réalisé par : Mamadou Ciré Bah, Ibrahim Diakité, Aboubacar Demba Bah, Mariama Ndour Sagne

Structure du projet

I)Le projet contient les fichiers principaux suivants :

- app.py -> Contient l'API Flask avec les routes principales
- database.py -> Définit les modèles Peewee (Product, Order, OrderItem).
- tasks.py -> Contient la fonction de traitement des paiements .
- cache.py -> Initialise le client Redis.
- config.py -> Configure l'application Flask, Redis et la queue RQ
- fetch_products.py -> Récupère les produits depuis une API distante et les insère en base.
- test_unitaire.py -> Fichier de tests unitaires avec unittest.
- Dockerfile -> Permet de builder l'image Docker de l'application.
- docker-compose.yml -> Lance les services nécessaires : PostgreSQL, Redis, Web, Worker.
- wait-for-postgres.sh -> Script pour attendre que PostgreSQL soit prêt avant de lancer Flask.
- requirements.txt -> Liste des dépendances Python du projet.

II)Lancement avec Docker

Voici les étapes pour construire et exécuter l’application avec Docker :

1. Construction des images Docker :
   docker-compose build

2. Lancement de l’application et de ses services :
   docker-compose up

Cela va automatiquement démarrer les services suivants :
- PostgreSQL (port 5432)
- Redis (port 6379)
- Web (Flask) (port 5000)
- Worker (RQ) pour exécuter les paiements en tâche de fond

3. Accès à l’interface :
   http://localhost:5000/ pour afficher la liste des produits
   http://localhost:5000/page/index.html pour accéder à la page web Interface utilisateur HTML 

4. Initialisation manuelle de la base de données (si nécessaire) :
   docker-compose exec web flask init-db

Toutes les variables d’environnement sont déjà configurées via le fichier database.py

Dépendances principales

- Flask
- peewee
- psycopg2-binary
- redis
- rq
- requests
