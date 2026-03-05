#!/usr/bin/env python3
"""
Script de inicialización de la base de datos.

Uso:
    python3 init_db.py --db ~/inventario/db/inventario.db [--seed]

Crea todas las tablas definidas en los modelos SQLAlchemy y,
opcionalmente, inserta datos de ejemplo (--seed).
"""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Inicializar la base de datos de inventario.")
    parser.add_argument("--db", required=True, help="Ruta al fichero SQLite (se crea si no existe).")
    parser.add_argument("--seed", action="store_true", help="Insertar datos de ejemplo.")
    args = parser.parse_args()

    db_path = os.path.expanduser(args.db)
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Configurar el engine apuntando a la ruta indicada
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    # Importar modelos DESPUÉS de ajustar la ruta para que Base los recoja
    # Añadimos el directorio del script al path si hace falta
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from app.db import Base
    from app import models  # noqa: F401  – registra todos los modelos en Base.metadata

    Base.metadata.create_all(bind=engine)
    print(f"✅  Tablas creadas en {db_path}")

    if args.seed:
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        db = Session()
        try:
            _seed(db, models)
            db.commit()
            print("🌱  Datos de ejemplo insertados.")
        finally:
            db.close()


def _seed(db, models):
    from sqlalchemy import select
    from app.utils import normalize_text

    # Categorías
    categorias_seed = ["Lácteos", "Cereales", "Legumbres", "Verduras", "Frutas", "Carnes", "Conservas", "Otros"]
    cat_map = {}
    for nombre in categorias_seed:
        c = db.execute(select(models.Categoria).where(models.Categoria.nombre == nombre)).scalar_one_or_none()
        if not c:
            c = models.Categoria(nombre=nombre)
            db.add(c)
            db.flush()
        cat_map[nombre] = c.id

    # Ubicaciones
    ubicaciones_seed = ["Despensa", "Nevera", "Congelador", "Armario cocina"]
    for nombre in ubicaciones_seed:
        u = db.execute(select(models.Ubicacion).where(models.Ubicacion.nombre == nombre)).scalar_one_or_none()
        if not u:
            db.add(models.Ubicacion(nombre=nombre))

    db.flush()

    # Productos de ejemplo
    productos_seed = [
        ("Huevos", "Otros", 6),
        ("Arroz", "Cereales", 1),
        ("Leche entera", "Lácteos", 2),
        ("Lentejas", "Legumbres", 1),
        ("Zanahoria", "Verduras", 0),
    ]
    for nombre, cat_nombre, stock_min in productos_seed:
        nombre_norm = normalize_text(nombre)
        p = db.execute(select(models.Producto).where(models.Producto.nombre_norm == nombre_norm)).scalar_one_or_none()
        if not p:
            p = models.Producto(
                categoria_id=cat_map[cat_nombre],
                nombre_canonico=nombre,
                nombre_norm=nombre_norm,
                stock_minimo=stock_min,
            )
            db.add(p)
            db.flush()
            db.add(models.ProductoNombre(
                producto_id=p.id,
                idioma="es",
                tipo="DISPLAY",
                nombre=nombre,
                nombre_norm=nombre_norm,
                prioridad=10,
            ))

    db.flush()


if __name__ == "__main__":
    main()
