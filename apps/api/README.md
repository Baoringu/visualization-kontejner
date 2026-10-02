# API development

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e 'apps/api[test]'
docker compose -f infra/compose.yaml up -d postgres redis
PYTHONPATH=apps/api/src alembic -c apps/api/alembic.ini upgrade head
PYTHONPATH=apps/api/src python -m app.cli --password 'change-this-locally'
PYTHONPATH=apps/api/src uvicorn app.main:app --reload --port 8000
```

The seed is explicit and must not run on application startup. The password above is only an example for a local development database.
