# Turf backend

## Instructions

0. Set environment variables

```sh
ENVIRONMENT="DEVELOPMENT"
# Ther user will be created with the specified password once the container is up and running.
POSTGRES_USER="user"
POSTGRES_PASSWORD="password"
POSTGRES_HOST="localhost"
DB_PORT=5432
POSTGRES_DATABASE="TURF"
POSTGRES_URL="postgresql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_NAME}"
```

1. Run database container

```sh
docker-compose up -d
```

2. Install dependencies

```sh
pipenv install --dev
```

3. Run virtual environment

```sh
pipenv shell
```

4. Run the application

```sh
fastapi dev main.py
```

## Important information

This application is deployed on Render -> https://turf-backend-h6nc.onrender.com
You can check the documentation of the application (we are using Swagger) here: https://turf-backend-h6nc.onrender.com/docs
