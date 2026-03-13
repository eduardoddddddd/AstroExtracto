"""
reindex_v2.py — Reindexado con normalización de texto y chunks más pequeños
===========================================================================
Mejoras respecto a reindex_limpio.py:

1. NORMALIZACIÓN: lowercase + quitar acentos con unidecode, tanto al indexar
   como al buscar. Así "Júpiter" = "Jupiter" = "jupiter" para el modelo.

2. FILTRO DE FILLER: se eliminan muletillas del lenguaje hablado coloquial
   español ("bueno", "pues", "eh", "a ver"...) que contaminaban los vectores.

3. CHUNK SIZE REDUCIDO: de 300 a 120 palabras. Los chunks de transcripción
   hablada tienen ~40% de contenido real — chunks más pequeños = más señal,
   menos ruido por vector.

DEPENDENCIAS: chromadb, sentence-transformers, unidecode
USO: python reindex_v2.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import os, re, json
import chromadb
from sentence_transformers import SentenceTransformer
from unidecode import unidecode

CHROMA_PATH   = "C:/Users/Edu/Downloads/chroma_db"
VTT_DIR       = "C:/Users/Edu/Downloads/corpus_astro/Isabel Pareja Astrología terapéutica y evolutiva"
COLECCION     = "astro_corpus"
CHUNK_SIZE    = 120   # reducido de 300 — lenguaje hablado tiene mucho ruido
CHUNK_OVERLAP = 20
MODELO        = "paraphrase-multilingual-MiniLM-L12-v2"

# Muletillas del español hablado coloquial que contaminan los vectores
FILLER = {
    'eh', 'ah', 'oh', 'mm', 'um', 'bueno', 'pues', 'entonces', 'osea', 'o sea',
    'a ver', 'venga', 'vale', 'claro', 'hombre', 'oye', 'mira', 'vamos',
    'nada', 'tal', 'tipo', 'digamos', 'no se', 'verdad', 'sabes',
}

def normalizar(texto):
    """Lowercase + quitar acentos. Así Júpiter == Jupiter == jupiter."""
    return unidecode(texto.lower())

def limpiar_filler(texto):
    """Elimina muletillas del español hablado."""
    palabras = texto.split()
    resultado = []
    i = 0
    while i < len(palabras):
        # Probar bigrama primero
        if i + 1 < len(palabras):
            bigrama = palabras[i] + ' ' + palabras[i+1]
            if bigrama in FILLER:
                i += 2
                continue
        if palabras[i] not in FILLER:
            resultado.append(palabras[i])
        i += 1
    return ' '.join(resultado)

def limpiar_vtt(texto_vtt):
    texto = re.sub(r'<\d{2}:\d{2}:\d{2}[\.,]\d{3}>', '', texto_vtt)
    texto = re.sub(r'</?[cbi]>', '', texto)
    texto = re.sub(r'<[^>]+>', '', texto)

    lineas = texto.split('\n')
    resultado = []
    vistas = set()
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        if linea.startswith('WEBVTT'): continue
        if linea.startswith('Kind:'): continue
        if linea.startswith('Language:'): continue
        if re.match(r'^\d{2}:\d{2}:\d{2}[\.,]\d{3}\s*-->', linea): continue
        if re.match(r'^\d+$', linea): continue
        if linea in vistas: continue
        vistas.add(linea)
        resultado.append(linea)

    texto_final = ' '.join(resultado)
    texto_final = re.sub(r'\s+', ' ', texto_final).strip()
    return texto_final

def hacer_chunks(texto_original, meta_base):
    """
    Genera chunks con dos versiones del texto:
    - texto_busqueda: normalizado (sin acentos, lowercase, sin filler) → para el embedding
    - texto_display: limpio pero legible → guardado en ChromaDB para mostrar al usuario
    """
    palabras = texto_original.split()
    chunks = []
    i = 0
    chunk_num = 0
    while i < len(palabras):
        segmento = ' '.join(palabras[i:i + CHUNK_SIZE])
        if len(segmento.strip()) > 30:
            # Versión para embedding: normalizada y sin filler
            texto_embed = limpiar_filler(normalizar(segmento))
            meta = dict(meta_base)
            meta['chunk'] = chunk_num
            meta['texto_original'] = segmento  # guardamos el original para display
            chunks.append({
                'texto_embed': texto_embed,
                'texto_display': segmento,
                'meta': meta
            })
            chunk_num += 1
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def leer_info_json(ruta_json):
    try:
        with open(ruta_json, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
        return {
            'titulo': data.get('title', 'Sin titulo')[:200],
            'video_id': data.get('id', ''),
            'url': data.get('webpage_url', ''),
            'canal': data.get('uploader', 'Isabel Pareja'),
        }
    except:
        return None

print("=" * 60)
print("PASO 1: Borrando coleccion...")
client = chromadb.PersistentClient(path=CHROMA_PATH)
try:
    client.delete_collection(COLECCION)
    print("Borrada.")
except:
    print("No existia.")

print("\nPASO 2: Cargando modelo...")
modelo = SentenceTransformer(MODELO)
print("Listo.")

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
            'titulo': '_'.join(partes[2:]).replace('.es.vtt', '').replace('.vtt', ''),
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
        print(f"   ERROR {archivo[:50]}: {e}")

print(f"\nTotal chunks: {len(todos_chunks)} | Errores: {errores}")

print("\n--- MUESTRA (primer chunk) ---")
print("DISPLAY:", todos_chunks[0]['texto_display'][:200])
print("EMBED:  ", todos_chunks[0]['texto_embed'][:200])
print("------------------------------\n")

print("PASO 4: Indexando...")
LOTE = 100
total = len(todos_chunks)

for inicio in range(0, total, LOTE):
    fin = min(inicio + LOTE, total)
    lote = todos_chunks[inicio:fin]
    # embedding sobre texto normalizado, pero guardamos el texto display legible
    textos_embed   = [c['texto_embed']   for c in lote]
    textos_display = [c['texto_display'] for c in lote]
    metas          = [c['meta']          for c in lote]
    ids            = [f"{c['meta']['video_id']}_c{c['meta']['chunk']}_{inicio}" for c in lote]
    embeddings     = modelo.encode(textos_embed, show_progress_bar=False).tolist()
    col.add(documents=textos_display, embeddings=embeddings, metadatas=metas, ids=ids)
    pct = int((fin / total) * 100)
    if fin % 2000 == 0 or fin == total:
        print(f"   [{pct:3d}%] {fin}/{total}")

print(f"\nCOMPLETADO: {col.count()} chunks indexados")
