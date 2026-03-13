"""
check_chroma2.py — Inspección de calidad de chunks en ChromaDB
===============================================================
Versión ampliada del diagnóstico. Además de contar documentos,
ejecuta búsquedas de prueba directamente con query_texts (sin
modelo de embeddings externo — ChromaDB usa su propio embedding
interno si no se pasa query_embeddings).

Se usó para detectar el problema de texto triplicado antes del
reindexado limpio: los chunks devueltos mostraban fragmentos
repetidos como "residencia, casa, familia, residencia, casa...".

USO: python check_chroma2.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import chromadb

client = chromadb.PersistentClient(path="C:/Users/Edu/Downloads/chroma_db")
col = client.get_collection('astro_corpus')

print(f"Total chunks: {col.count()}")
print()

print("=" * 60)
print("BUSQUEDA: 'Jupiter en casa 2'")
print("=" * 60)
resultados = col.query(
    query_texts=["Jupiter en casa 2"],
    n_results=3
)

for i, (doc, meta) in enumerate(zip(resultados['documents'][0], resultados['metadatas'][0])):
    print(f"\n--- Resultado {i+1} ---")
    print(f"Fuente: {meta}")
    print(f"Texto: {repr(doc[:300])}")

print()
print("=" * 60)
print("BUSQUEDA: 'Saturno restriccion emocional'")
print("=" * 60)
resultados2 = col.query(
    query_texts=["Saturno restriccion emocional"],
    n_results=3
)

for i, (doc, meta) in enumerate(zip(resultados2['documents'][0], resultados2['metadatas'][0])):
    print(f"\n--- Resultado {i+1} ---")
    print(f"Fuente: {meta}")
    print(f"Texto: {repr(doc[:300])}")
