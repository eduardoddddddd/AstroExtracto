"""
check_chroma.py — Diagnóstico de ChromaDB
==========================================
Script de diagnóstico que busca la base de datos ChromaDB en rutas
comunes y muestra las colecciones existentes con su conteo de documentos.

Útil para verificar que la BD existe y tiene datos antes de lanzar
el indexador o la interfaz principal.

USO: python check_chroma.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import chromadb
import os

rutas = [
    "C:/Users/Edu/Downloads/chroma_db",
    "C:/Users/Edu/AstroExtracto/chroma_db",
    "C:/chroma_db",
]

for ruta in rutas:
    if os.path.exists(ruta):
        print(f"BD encontrada en: {ruta}")
        try:
            client = chromadb.PersistentClient(path=ruta)
            colecciones = client.list_collections()
            print(f"Colecciones: {len(colecciones)}")
            for col in colecciones:
                c = client.get_collection(col.name)
                print(f"  - '{col.name}': {c.count()} documentos indexados")
        except Exception as e:
            print(f"  Error al abrir: {e}")
    else:
        print(f"No existe: {ruta}")
