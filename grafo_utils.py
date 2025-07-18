import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import io

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import aliased
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

class Provincia(db.Model):
    __tablename__ = 'provincias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    is_costera = db.Column(db.Boolean, nullable=False, default=False)
    visitas = db.Column(db.Integer, nullable=False, default=0)


class Conexion(db.Model):
    __tablename__ = 'conexiones'
    id = db.Column(db.Integer, primary_key=True)
    origen_id = db.Column(db.Integer, db.ForeignKey('provincias.id'), nullable=False)
    destino_id = db.Column(db.Integer, db.ForeignKey('provincias.id'), nullable=False)
    distancia = db.Column(db.Integer, nullable=False)

class CiudadCostera(db.Model):
    __tablename__ = 'ciudades_costeras'
    provincia_id = db.Column(db.Integer, db.ForeignKey('provincias.id'), primary_key=True)

class Ruta(db.Model):
    __tablename__ = 'rutas'
    id = db.Column(db.Integer, primary_key=True)
    origen = db.Column(db.String(100), nullable=False)
    destino = db.Column(db.String(100), nullable=False)
    camino = db.Column(db.Text, nullable=False)   # JSON string
    costo = db.Column(db.Integer, nullable=False)
    valido = db.Column(db.Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint('origen', 'destino', name='uq_origen_destino'),
    )

def construir_grafo():
    G = nx.Graph()
    Origen = aliased(Provincia)
    Destino = aliased(Provincia)

    conexiones = db.session.query(Conexion, Origen, Destino)\
        .join(Origen, Conexion.origen_id == Origen.id)\
        .join(Destino, Conexion.destino_id == Destino.id)\
        .all()

    for conexion, origen, destino in conexiones:
        G.add_edge(origen.nombre, destino.nombre, weight=conexion.distancia)
    return G

def obtener_costeras():
    rows = db.session.query(Provincia.nombre)\
        .join(CiudadCostera, Provincia.id == CiudadCostera.provincia_id)\
        .all()
    return {nombre for (nombre,) in rows}

def camino_optimo_con_costera(origen, destino):
    # 1) intenta leer cache
    ruta_cache = Ruta.query.filter_by(origen=origen, destino=destino).first()
    if ruta_cache:
        camino = json.loads(ruta_cache.camino)
        return {"camino": camino, "costo": ruta_cache.costo, "valido": ruta_cache.valido}

    # 2) si no existe, calcular
    G = construir_grafo()
    COSTERAS = obtener_costeras()
    try:
        camino = nx.dijkstra_path(G, origen, destino, weight='weight')
        costo = nx.dijkstra_path_length(G, origen, destino, weight='weight')
        valido = any(ciudad in COSTERAS for ciudad in camino)
    except nx.NetworkXNoPath:
        camino, costo, valido = [], None, False

    # 3) guardar en cache
    nueva = Ruta(
        origen=origen,
        destino=destino,
        camino=json.dumps(camino, ensure_ascii=False),
        costo=costo or 0,
        valido=valido
    )
    db.session.add(nueva)
    db.session.commit()

    return {"camino": camino, "costo": costo, "valido": valido}

def obtener_ciudades():
    provincias = Provincia.query.order_by(Provincia.nombre).all()
    return [p.nombre for p in provincias]

def grafo_a_imagen():
    G = construir_grafo()
    pos = nx.spring_layout(G, seed=42)
    pesos = nx.get_edge_attributes(G, 'weight')

    fig, ax = plt.subplots(figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, node_color='lightblue',
            node_size=2000, font_weight='bold')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=pesos)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf
