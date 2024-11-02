# Turf backend

## Instructions

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
