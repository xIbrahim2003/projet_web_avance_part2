# Utiliser une image de base Python
FROM python:3.12
# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers du projet dans le conteneur
COPY . . 

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Définir la variable d'environnement FLASK_APP
ENV FLASK_APP=app.py

# Exposer le port 5000
EXPOSE 5000

COPY wait-for-postgres.sh /wait-for-postgres.sh
RUN chmod +x /wait-for-postgres.sh
RUN apt-get update && apt-get install -y netcat-openbsd


# Lancer l'application
CMD ["flask", "run", "--host=0.0.0.0"]
