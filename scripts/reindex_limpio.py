"""
reindex_limpio.py — Reindexado limpio de ChromaDB desde corpus VTT
===================================================================
Script de utilidad para borrar y reconstruir desde cero la colección
ChromaDB 'astro_corpus' a partir de los 277 archivos .vtt del canal
de Isabel Pareja.

PROBLEMA QUE RESUELVE:
Los VTTs de YouTube tienen dos capas de ruido que contaminan el texto:
  1. Líneas triplicadas por solapamiento de subtítulos
  2. Etiquetas de sincronización palabra a palabra: <00:43:00.480><c>texto</c>

Sin limpiar, ChromaDB acumulaba 46.289 chunks con texto incoherente.
Con limpieza en dos capas (regex + deduplicación), quedan 5.252 chunks
limpios con castellano legible y búsquedas relevantes.

DEPENDENCIAS: chromadb, sentence-transformers
RUTAS: ajustar CHROMA_PATH y VTT_DIR según tu instalación
USO: python reindex_limpio.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import os, re, json
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "C:/Users/Edu/Downloads/chroma_db"
VTT_DIR     = "C:/Users/Edu/Downloads/corpus_astro/Isabel Pareja Astrología terapéutica y evolutiva"
COLECCION   = "astro_corpus"
CHUNK_SIZE  = 300
CHUNK_OVERLAP = 50
MODELO      = "paraphrase-multilingual-MiniLM-L12-v2"

def limpiar_vtt(texto_vtt):
    # Capa 1: eliminar etiquetas VTT de sincronización
    texto = re.sub(r'<\d{2}:\d{2}:\d{2}[\.,]\d{3}>', '', texto_vtt)
    texto = re.sub(r'</?c>', '', texto)
    texto = re.sub(r'</?b>', '', texto)
    texto = re.sub(r'</?i>', '', texto)
    texto = re.sub(r'<[^>]+>', '', texto)

    # Capa 2: eliminar líneas duplicadas y timestamps
    lineas = texto.split('\n')
    resultado = []
    vistas = set()
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        if linea.startswith('WEBVTT'): continue
        if re.match(r'^\d{2}:\d{2}:\d{2}[\.,]\d{3}\s*-->', linea): continue
        if re.match(r'^\d+$', linea): continue
        if linea in vistas: continue
        vistas.add(linea)
        resultado.append(linea)

    texto_final = ' '.join(resultado)
    texto_final = re.sub(r'\s+', ' ', texto_final).strip()
    return texto_final

def hacer_chunks(texto, meta_base, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    palabras = texto.split()
    chunks = []
    i = 0
    chunk_num = 0
    while i < len(palabras):
        chunk_texto = ' '.join(palabras[i:i + chunk_size])
        if len(chunk_texto.strip()) > 50:
            meta = dict(meta_base)
            meta['chunk'] = chunk_num
            chunks.append({'texto': chunk_texto, 'meta': meta})
            chunk_num += 1
        i += chunk_size - overlap
    return chunks

def leer_info_json(ruta_json):
    try:
        with open(ruta_json, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
        return {
            'titulo': data.get('title', 'Sin título')[:200],
            'video_id': data.get('id', ''),
            'url': data.get('webpage_url', ''),
            'canal': data.get('uploader', 'Isabel Pareja'),
        }
    except:
        return None

print("=" * 60)
print("PASO 1: Borrando colección...")
client = chromadb.PersistentClient(path=CHROMA_PATH)
try:
    client.delete_collection(COLECCION)
    print("✅ Borrada.")
except:
    print("ℹ️  No existía.")

print("\nPASO 2: Cargando modelo...")
modelo = SentenceTransformer(MODELO)
print("✅ Listo.")

col = client.get_or_create_collection(COLECCION)

print(f"\nPASO 3: Procesando VTTs...")
archivos_vtt = sorted([f for f in os.listdir(VTT_DIR) if f.endswith('.vtt') and not f.endswith('.info.json')])

todos_chunks = []
errores = 0

for i, archivo in enumerate(archivos_vtt):
    ruta_vtt = os.path.join(VTT_DIR, archivo)
    ruta_json = ruta_vtt.replace('.es.vtt', '.info.json').replace('.vtt', '.info.json')
    meta = leer_info_json(ruta_json)

    if not meta:
        partes = archivo.split('_')
        video_id = partes[1] if len(partes) > 1 else archivo
        meta = {
            'titulo': '_'.join(partes[2:]).replace('.es.vtt','').replace('.vtt',''),
            'video_id': video_id,
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'canal': 'Isabel Pareja',
        }

    try:
        with open(ruta_vtt, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read()
        texto_limpio = limpiar_vtt(contenido)
        if len(texto_limpio.strip()) < 100:
            continue
        chunks = hacer_chunks(texto_limpio, meta)
        todos_chunks.extend(chunks)
        if (i + 1) % 50 == 0:
            print(f"   [{i+1}/{len(archivos_vtt)}] chunks: {len(todos_chunks)}")
    except Exception as e:
        errores += 1
        print(f"   ❌ {archivo[:50]} — {e}")

print(f"\n✅ Total chunks limpios: {len(todos_chunks)} | Errores: {errores}")

print("\n--- MUESTRA DE TEXTO LIMPIO (primer chunk) ---")
print(todos_chunks[0]['texto'][:300])
print("----------------------------------------------\n")

print("PASO 4: Indexando...")
LOTE = 100
total = len(todos_chunks)

for inicio in range(0, total, LOTE):
    fin = min(inicio + LOTE, total)
    lote = todos_chunks[inicio:fin]
    textos     = [c['texto'] for c in lote]
    metas      = [c['meta']  for c in lote]
    ids        = [f"{c['meta']['video_id']}_c{c['meta']['chunk']}_{inicio}" for c in lote]
    embeddings = modelo.encode(textos, show_progress_bar=False).tolist()
    col.add(documents=textos, embeddings=embeddings, metadatas=metas, ids=ids)
    pct = int((fin / total) * 100)
    if fin % 1000 == 0 or fin == total:
        print(f"   [{pct:3d}%] {fin}/{total}")

print(f"\n✅ COMPLETADO — {col.count()} chunks indexados")
