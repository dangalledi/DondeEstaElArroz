🥚 Inventario Raspberry API

Inventario doméstico con SQLite + FastAPI.

Crear DB
```
mkdir -p ~/inventario/db

python3 ~/inventario/init_db.py \
  --db ~/inventario/db/inventario.db \
  --seed
```

Verificar:
```
sqlite3 ~/inventario/db/inventario.db ".tables"
```

API
Entorno
```
mkdir -p ~/inventario/api
cd ~/inventario/api

python3 -m venv .venv
source .venv/bin/activate

pip install fastapi uvicorn "sqlalchemy>=2.0" pydantic
```

Ejecutar API
```
cd ~/inventario/api
source .venv/bin/activate

uvicorn app.main:app --host 0.0.0.0 --port 8000
```
