#!/bin/sh
# wait-for-postgres.sh

host="$1"
port="$2"
shift 2

echo "Attente que PostgreSQL soit prêt à $host:$port..."

until nc -z "$host" "$port"; do
  echo "En attente de PostgreSQL à $host:$port..."
  sleep 1
done

echo "PostgreSQL est prêt, lancement de la commande : $@"
exec "$@"