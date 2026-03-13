"""
test_busqueda.py — Pruebas de búsqueda semántica con embeddings reales
=======================================================================
Valida la calidad del corpus indexado ejecutando búsquedas usando el
mismo modelo de embeddings (MiniLM-L12-v2) que usa la interfaz principal.

A diferencia de check_chroma2.py (que usa el embedding interno de
ChromaDB), este script genera los embeddings externamente y los pasa
como query_embeddings, replicando exactamente el comportamiento de
astro_corpus_ui.py.

Se ejecutó tras el reindexado limpio para confirmar que los resultados
eran coherentes y el texto estaba libre de ruido VTT.

Resultado esperado: chunks de 250-300 palabras en castellano limpio,
con títulos de vídeo reconocibles y contenido temáticamente relevante.

USO: python test_busqueda.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="C:/Users/Edu/Downloads/chroma_db")
col = client.get_collection("astro_corpus")
modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print(f"Total chunks limpios: {col.count()}\n")

def buscar(consulta, n=3):
    print("=" * 60)
    print(f"BUSQUEDA: '{consulta}'")
    print("=" * 60)
    emb = modelo.encode([consulta]).tolist()
    res = col.query(query_embeddings=emb, n_results=n)
    for i, (doc, meta) in enumerate(zip(res['documents'][0], res['metadatas'][0])):
        print(f"\n--- Resultado {i+1} ---")
        print(f"Titulo: {meta.get('titulo','?')[:80]}")
        print(f"Texto:  {doc[:250]}")
    print()

buscar("Jupiter en casa 2 abundancia dinero")
buscar("Saturno bloqueo emocional restriccion")
buscar("Luna llena rituales manifestacion")
