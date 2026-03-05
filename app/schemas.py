from pydantic import BaseModel, Field
from typing import Optional, List

class CategoriaCreate(BaseModel):
    nombre: str

class CategoriaOut(BaseModel):
    id: int
    nombre: str
    class Config:
        from_attributes = True

class UbicacionCreate(BaseModel):
    nombre: str

class UbicacionOut(BaseModel):
    id: int
    nombre: str
    class Config:
        from_attributes = True

class ProductoNombreCreate(BaseModel):
    idioma: str = Field(examples=["ca", "es", "en"])
    tipo: str = Field(default="ALIAS", examples=["ALIAS", "DISPLAY"])
    nombre: str
    prioridad: int = Field(default=0)

class ProductoNombreOut(BaseModel):
    id: int
    producto_id: int
    idioma: str
    tipo: str
    nombre: str
    prioridad: int
    class Config:
        from_attributes = True

class StockItem(BaseModel):
    producto_id: int
    nombre_canonico: str
    stock_actual: int
    stock_minimo: int

class ProductoCreate(BaseModel):
    categoria_id: int
    nombre_canonico: str
    stock_minimo: int = 0

class ProductoOut(BaseModel):
    id: int
    categoria_id: int
    nombre_canonico: str
    stock_minimo: int
    class Config:
        from_attributes = True

class TicketCreate(BaseModel):
    fecha: str = Field(examples=["2026-02-15"])
    comercio: Optional[str] = Field(default=None, examples=["CL HOSPITAL 131"])
    total_monto: Optional[float] = Field(default=None, examples=[26.87])
    imagen_path: Optional[str] = Field(default=None, examples=["/data/tickets/2026/02/15/501.jpg"])

class TicketLineaCreate(BaseModel):
    raw_text: str = Field(examples=["TOMAQUET FREGIT VEGE"])
    cantidad_detectada: Optional[int] = Field(default=1, examples=[1])
    total_linea_detectado: Optional[float] = Field(default=None, examples=[0.95])

class TicketOut(BaseModel):
    id: int
    fecha: str
    comercio: Optional[str]
    total_monto: Optional[float]
    status: str
    class Config:
        from_attributes = True

class TicketLineaPatch(BaseModel):
    producto_confirmado_id: Optional[int] = Field(default=None, examples=[12])
    vencimiento_confirmado: Optional[str] = Field(default=None, examples=["2026-02-18"])
    ubicacion_id: Optional[int] = Field(default=None, examples=[2])
    status: Optional[str] = Field(default=None, examples=["OK"])
    nota: Optional[str] = Field(default=None, examples=["aplicar descuento a esta línea"])

class ConsumeReq(BaseModel):
    producto: str = Field(examples=["huevos", "zanahoria", "pastanaga"])
    cantidad: int = Field(ge=1, default=1, examples=[1])
    origen: str = Field(default="api", examples=["telegram", "dashboard"])
    nota: Optional[str] = Field(default=None, examples=["hice tortilla"])

class SetReq(BaseModel):
    producto: str = Field(examples=["huevos", "pastanaga"])
    cantidad: int = Field(ge=0, examples=[5])
    origen: str = Field(default="api", examples=["telegram", "dashboard"])
    nota: Optional[str] = Field(default=None, examples=["conteo manual en nevera"])

class TicketLineaOut(BaseModel):
    id: int
    raw_text: str
    cantidad: Optional[int] = None
    total: Optional[float] = None
    status: str
    producto_confirmado_id: Optional[int] = None
    vencimiento: Optional[str] = None
    ubicacion_id: Optional[int] = None
    nota: Optional[str] = None

class TicketListItem(BaseModel):
    id: int
    fecha: str
    comercio: Optional[str] = None
    total: Optional[float] = None
    status: str

class CommitOut(BaseModel):
    ok: bool
    lotes_creados: int
    ticket_status: str

class OkOut(BaseModel):
    ok: bool