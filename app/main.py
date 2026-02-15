from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .db import get_db
from .utils import normalize_text
from . import models, schemas

from fastapi import FastAPI

DESCRIPTION = """
API de inventario doméstico (Raspberry Pi).

### Flujo principal
1) **Inbox**: creas un ticket y subes líneas (OCR crudo).
2) **Review**: confirmas producto, vencimiento, ubicación; guardas aliases (ca/es).
3) **Commit**: genera **lotes** + **movimientos (COMPRA)**.
4) **Uso diario**: **consume** (restar) o **set** (ajuste por conteo).

### Convenciones
- Cantidades siempre en **unidades**.
- Tickets/lineas tienen estados: `PENDING_REVIEW|COMPLETED|IGNORED` y `NEEDS_REVIEW|OK|IGNORED`.
"""

app = FastAPI(
    title="Inventario Raspberry API",
    version="0.1.0",
    description=DESCRIPTION,
    contact={"name": "PataCorp", "url": "http://patana.local"},
)

app.openapi_tags = [
    {"name": "Productos", "description": "Catálogo canónico + alias multiidioma."},
    {"name": "Tickets", "description": "Inbox → Review → Commit."},
    {"name": "Inventario", "description": "Consumo y ajustes por conteo."},
]

# -------------------------
# Productos
# -------------------------
@app.post(
  "/productos",
  response_model=schemas.ProductoOut,
  tags=["Productos"],
  summary="Crear producto",
  description="Crea un producto canónico (castellano) y genera alias DISPLAY automáticamente."
)
def crear_producto(payload: schemas.ProductoCreate, db: Session = Depends(get_db)):
    nombre_norm = normalize_text(payload.nombre_canonico)
    exists = db.execute(select(models.Producto).where(models.Producto.nombre_norm == nombre_norm)).scalar_one_or_none()
    if exists:
        return exists
    p = models.Producto(
        categoria_id=payload.categoria_id,
        nombre_canonico=payload.nombre_canonico.strip(),
        nombre_norm=nombre_norm,
        stock_minimo=payload.stock_minimo,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    # Alias DISPLAY en es (opcional)
    db.add(models.ProductoNombre(
        producto_id=p.id, idioma="es", tipo="DISPLAY",
        nombre=p.nombre_canonico, nombre_norm=nombre_norm, prioridad=10
    ))
    db.commit()
    return p

@app.get("/productos", response_model=list[schemas.ProductoOut], tags=["Productos"])
def listar_productos(db: Session = Depends(get_db)):
    return db.execute(select(models.Producto).order_by(models.Producto.nombre_canonico)).scalars().all()

def resolve_producto_id(db: Session, user_text: str) -> int:
    q = normalize_text(user_text)
    # 1) match por nombre_norm en productos
    p = db.execute(select(models.Producto).where(models.Producto.nombre_norm == q)).scalar_one_or_none()
    if p:
        return p.id
    # 2) match por alias
    alias = db.execute(select(models.ProductoNombre).where(models.ProductoNombre.nombre_norm == q)).scalar_one_or_none()
    if alias:
        return alias.producto_id
    raise HTTPException(status_code=404, detail=f"Producto no encontrado: '{user_text}'")

# -------------------------
# Tickets (Inbox)
# -------------------------
@app.post("/tickets", response_model=schemas.TicketOut, tags=["Tickets"])
def crear_ticket(payload: schemas.TicketCreate, db: Session = Depends(get_db)):
    t = models.Ticket(
        fecha=payload.fecha,
        comercio=payload.comercio,
        total_monto=payload.total_monto,
        imagen_path=payload.imagen_path,
        status="PENDING_REVIEW",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

@app.post("/tickets/{ticket_id}/lineas", tags=["Tickets"])
def add_lineas_ticket(ticket_id: int, lineas: list[schemas.TicketLineaCreate], db: Session = Depends(get_db)):
    t = db.execute(select(models.Ticket).where(models.Ticket.id == ticket_id)).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Ticket no existe")
    for ln in lineas:
        db.add(models.TicketLinea(
            ticket_id=ticket_id,
            raw_text=ln.raw_text,
            raw_text_norm=normalize_text(ln.raw_text),
            cantidad_detectada=ln.cantidad_detectada,
            total_linea_detectado=ln.total_linea_detectado,
            status="NEEDS_REVIEW",
        ))
    db.commit()
    return {"ok": True, "added": len(lineas)}

@app.get("/tickets", tags=["Tickets"], response_model=list[schemas.TicketListItem])
def listar_tickets(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(models.Ticket).order_by(models.Ticket.id.desc())
    if status:
        stmt = stmt.where(models.Ticket.status == status)
    tickets = db.execute(stmt).scalars().all()
    return [{"id": t.id, "fecha": t.fecha, "comercio": t.comercio, "total": t.total_monto, "status": t.status} for t in tickets]

@app.get("/tickets/{ticket_id}/lineas", tags=["Tickets"], response_model=list[schemas.TicketLineaOut])
def listar_lineas(ticket_id: int, db: Session = Depends(get_db)):
    lines = db.execute(select(models.TicketLinea).where(models.TicketLinea.ticket_id == ticket_id)).scalars().all()
    return [{
        "id": l.id, "raw_text": l.raw_text, "cantidad": l.cantidad_detectada,
        "total": l.total_linea_detectado, "status": l.status,
        "producto_confirmado_id": l.producto_confirmado_id,
        "vencimiento": l.vencimiento_confirmado, "ubicacion_id": l.ubicacion_id,
        "nota": l.nota
    } for l in lines]

@app.patch("/ticket_lineas/{linea_id}", tags=["Tickets"])
def patch_linea(linea_id: int, payload: schemas.TicketLineaPatch, db: Session = Depends(get_db)):
    l = db.execute(select(models.TicketLinea).where(models.TicketLinea.id == linea_id)).scalar_one_or_none()
    if not l:
        raise HTTPException(404, "Línea no existe")

    if payload.producto_confirmado_id is not None:
        l.producto_confirmado_id = payload.producto_confirmado_id
    if payload.vencimiento_confirmado is not None:
        l.vencimiento_confirmado = payload.vencimiento_confirmado
    if payload.ubicacion_id is not None:
        l.ubicacion_id = payload.ubicacion_id
    if payload.status is not None:
        l.status = payload.status
    if payload.nota is not None:
        l.nota = payload.nota

    db.commit()
    return {"ok": True}

# -------------------------
# Commit: ticket -> lotes + movimientos COMPRA
# -------------------------
@app.post(
  "/tickets/{ticket_id}/commit",
  tags=["Tickets"],
  response_model=schemas.CommitOut,
  responses={
    400: {"description": "Ticket sin líneas / no hay líneas OK / línea sin producto_confirmado_id"},
    404: {"description": "Ticket no existe"},
  },
  summary="Confirmar ticket (commit)",
  description="Convierte las líneas OK en lotes + movimientos COMPRA y marca el ticket como COMPLETED."
)
def commit_ticket(ticket_id: int, db: Session = Depends(get_db)):
    t = db.execute(select(models.Ticket).where(models.Ticket.id == ticket_id)).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Ticket no existe")

    lineas = db.execute(select(models.TicketLinea).where(models.TicketLinea.ticket_id == ticket_id)).scalars().all()
    if not lineas:
        raise HTTPException(400, "Ticket sin líneas")

    # Solo procesamos las OK
    ok_lines = [l for l in lineas if l.status == "OK"]
    if not ok_lines:
        raise HTTPException(400, "No hay líneas OK para ingresar")

    created = 0
    for l in ok_lines:
        if not l.producto_confirmado_id:
            raise HTTPException(400, f"Línea {l.id} sin producto_confirmado_id")

        qty = l.cantidad_detectada or 1
        price = None
        # Si total_linea_detectado es total y qty>0, puedes derivar precio unidad (opcional)
        if l.total_linea_detectado is not None and qty > 0:
            price = float(l.total_linea_detectado) / float(qty)

        lote = models.Lote(
            producto_id=l.producto_confirmado_id,
            ticket_id=ticket_id,
            ubicacion_id=l.ubicacion_id,
            cantidad_inicial=qty,
            cantidad_actual=qty,
            precio_unidad=price,
            vencimiento=l.vencimiento_confirmado,
            esta_abierto=0,
            nota=None,
        )
        db.add(lote)
        db.flush()  # para tener lote.id sin commit

        mov = models.Movimiento(
            tipo="COMPRA",
            producto_id=l.producto_confirmado_id,
            lote_id=lote.id,
            ticket_id=ticket_id,
            cantidad=qty,
            precio_unidad=price,
            origen="ocr+review",
            nota=None,
        )
        db.add(mov)
        created += 1

    t.status = "COMPLETED"
    db.commit()
    return {"ok": True, "lotes_creados": created, "ticket_status": t.status}

# -------------------------
# Inventario: consume y set
# -------------------------
def fifo_lotes_con_stock(db: Session, producto_id: int):
    return db.execute(
        select(models.Lote)
        .where(models.Lote.producto_id == producto_id)
        .where(models.Lote.cantidad_actual > 0)
        .order_by(models.Lote.id.asc())
    ).scalars().all()

@app.post(
    "/inventario/consume",
    tags=["Inventario"],
    responses={
        400: {"description": "No hay stock suficiente"},
        404: {"description": "Producto no encontrado"},
    },
)
def consume(payload: schemas.ConsumeReq, db: Session = Depends(get_db)):
    producto_id = resolve_producto_id(db, payload.producto)

    remaining = payload.cantidad
    lotes = fifo_lotes_con_stock(db, producto_id)
    if not lotes:
        raise HTTPException(400, "No hay stock para consumir")

    for lote in lotes:
        if remaining <= 0:
            break
        take = min(lote.cantidad_actual, remaining)
        lote.cantidad_actual -= take
        db.add(models.Movimiento(
            tipo="CONSUMO",
            producto_id=producto_id,
            lote_id=lote.id,
            ticket_id=lote.ticket_id,
            cantidad=take,
            precio_unidad=lote.precio_unidad,
            origen=payload.origen,
            nota=payload.nota,
        ))
        remaining -= take

    if remaining > 0:
        raise HTTPException(400, f"Stock insuficiente, faltan {remaining} unidades")

    db.commit()
    return {"ok": True}

@app.post("/inventario/set", operation_id="set_stock", tags=["Inventario"])
def set_stock(payload: schemas.SetReq, db: Session = Depends(get_db)):
    """
    Ajusta el stock total de un producto al valor indicado (**conteo manual**).

    Ejemplo: `"quedan huevos 5"`.

    - Si el stock actual es mayor, descuenta la diferencia (FIFO).
    - Si el stock actual es menor, crea un lote de **ajuste manual**.
    """
    producto_id = resolve_producto_id(db, payload.producto)

    stock_total = db.execute(
        select(func.coalesce(func.sum(models.Lote.cantidad_actual), 0))
        .where(models.Lote.producto_id == producto_id)
    ).scalar_one()

    delta = int(payload.cantidad) - int(stock_total)

    if delta == 0:
        return {"ok": True, "message": "Sin cambios", "stock": int(stock_total)}

    if delta < 0:
        # consumir diferencia (FIFO)
        need = -delta
        lotes = fifo_lotes_con_stock(db, producto_id)
        for lote in lotes:
            if need <= 0:
                break
            take = min(lote.cantidad_actual, need)
            lote.cantidad_actual -= take
            db.add(models.Movimiento(
                tipo="AJUSTE",
                producto_id=producto_id,
                lote_id=lote.id,
                ticket_id=lote.ticket_id,
                cantidad=take,
                precio_unidad=lote.precio_unidad,
                origen=payload.origen,
                nota=payload.nota or f"set stock a {payload.cantidad}",
            ))
            need -= take
        if need > 0:
            raise HTTPException(400, f"No hay suficiente stock para ajustar, faltan {need}")
    else:
        # ajuste positivo: crear un lote manual
        lote = models.Lote(
            producto_id=producto_id,
            ticket_id=None,
            ubicacion_id=None,
            cantidad_inicial=delta,
            cantidad_actual=delta,
            precio_unidad=None,
            vencimiento=None,
            esta_abierto=0,
            nota="ajuste manual",
        )
        db.add(lote)
        db.flush()
        db.add(models.Movimiento(
            tipo="AJUSTE",
            producto_id=producto_id,
            lote_id=lote.id,
            ticket_id=None,
            cantidad=delta,
            precio_unidad=None,
            origen=payload.origen,
            nota=payload.nota or f"set stock a {payload.cantidad}",
        ))

    db.commit()
    new_total = db.execute(
        select(func.coalesce(func.sum(models.Lote.cantidad_actual), 0))
        .where(models.Lote.producto_id == producto_id)
    ).scalar_one()
    return {"ok": True, "delta": delta, "stock": int(new_total)}


@app.get("/health", tags=["Sistema"], response_model=schemas.OkOut)
def health():
    """Healthcheck simple."""
    return {"ok": True}
