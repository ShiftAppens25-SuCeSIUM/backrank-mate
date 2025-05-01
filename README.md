# BackRank Mate

Backend for CheckMate application.

## Getting Started

### Docker

1. To get started, build the Docker image

```bash
docker build -t backrank-mate .
```

2. and run it

```bash
docker run -p 8000:8000 backrank-mate
```

3. You can now access the API in `http://127.0.0.1:8000`.

### Python

1. (Optional) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the application

```bash
uvicorn app.main:app --reload
```

4. You can now access the API in `http://127.0.0.1:8000`.

## Using the API

A Postman collection describing out to use the API can be found in `docs/collection.json`.
