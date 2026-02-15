from sqlalchemy import (
    Column, Integer, Text, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from .db import Base

class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True)
    nombre = Column(Text, nullable=False, unique=True)

class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    id = Column(Integer, primary_key=True)
    nombre = Column(Text, nullable=False, unique=True)

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    nombre_canonico = Column(Text, nullable=False)
    nombre_norm = Column(Text, nullable=False, unique=True)
    stock_minimo = Column(Integer, nullable=False, default=0)
    vida_util_dias = Column(Integer, nullable=True)
    activo = Column(Integer, nullable=False, default=1)

    categoria = relationship("Categoria")

class ProductoNombre(Base):
    __tablename__ = "producto_nombres"
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    idioma = Column(Text, nullable=False, default="und")
    tipo = Column(Text, nullable=False, default="ALIAS")
    nombre = Column(Text, nullable=False)
    nombre_norm = Column(Text, nullable=False)
    prioridad = Column(Integer, nullable=False, default=0)

    producto = relationship("Producto")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    fecha = Column(Text, nullable=False)  # YYYY-MM-DD
    comercio = Column(Text, nullable=True)
    total_monto = Column(Float, nullable=True)
    moneda = Column(Text, nullable=False, default="EUR")
    imagen_path = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="PENDING_REVIEW")

class TicketLinea(Base):
    __tablename__ = "ticket_lineas"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)

    raw_text = Column(Text, nullable=False)
    raw_text_norm = Column(Text, nullable=False)

    cantidad_detectada = Column(Integer, nullable=True)
    precio_unit_detectado = Column(Float, nullable=True)
    total_linea_detectado = Column(Float, nullable=True)

    producto_sugerido_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    score_sugerido = Column(Float, nullable=True)

    producto_confirmado_id = Column(Integer, ForeignKey("productos.id"), nullable=True)

    vencimiento_confirmado = Column(Text, nullable=True)  # YYYY-MM-DD
    ubicacion_id = Column(Integer, ForeignKey("ubicaciones.id"), nullable=True)

    status = Column(Text, nullable=False, default="NEEDS_REVIEW")
    nota = Column(Text, nullable=True)

    ticket = relationship("Ticket")
    producto_confirmado = relationship("Producto", foreign_keys=[producto_confirmado_id])
    ubicacion = relationship("Ubicacion")

class Lote(Base):
    __tablename__ = "lotes"
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ubicacion_id = Column(Integer, ForeignKey("ubicaciones.id"), nullable=True)

    cantidad_inicial = Column(Integer, nullable=False)
    cantidad_actual = Column(Integer, nullable=False)

    precio_unidad = Column(Float, nullable=True)
    vencimiento = Column(Text, nullable=True)  # YYYY-MM-DD
    esta_abierto = Column(Integer, nullable=False, default=0)
    nota = Column(Text, nullable=True)

class Movimiento(Base):
    __tablename__ = "movimientos"
    id = Column(Integer, primary_key=True)
    timestamp = Column(Text, nullable=False)  # default lo pone SQLite
    tipo = Column(Text, nullable=False)       # COMPRA/CONSUMO/AJUSTE...

    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)

    cantidad = Column(Integer, nullable=False)
    precio_unidad = Column(Float, nullable=True)
    nota = Column(Text, nullable=True)
    origen = Column(Text, nullable=True)
