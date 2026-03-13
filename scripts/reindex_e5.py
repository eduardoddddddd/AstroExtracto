"""
reindex_e5.py — Reindexado con multilingual-e5-large + título prefijado en chunks
==================================================================================
Mejoras respecto a reindex_v2.py:

1. MODELO: intfloat/multilingual-e5-large (560M params, 1024 dims)
   vs paraphrase-multilingual-MiniLM-L12-v2 (117M, 384 dims)
   - Específicamente entrenado para retrieval (no traducción)
   - Discrimina mejor entre conceptos astrológicos específicos
   - "Casa 12" vs "casa 8" → vectores distintos

2. PREFIJO DE TÍTULO EN CHUNK: e5-large usa el prefijo "passage: " al indexar
   y "query: " al buscar (es su protocolo de entrenamiento).
   Además añadimos el título del vídeo como contexto al inicio de cada chunk,
   así el embedding incluye de qué vídeo viene el fragmento.

3. CHUNK SIZE: 150 palabras (ligeramente mayor que v2 para mejor coherencia)

NOTA: El reindexado tarda ~15-25 min en 277 VTTs con e5-large en CPU.
      Con RTX 4070 disponible se puede acelerar con device='cuda'.

USO: python reindex_e5.py
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
CHUNK_SIZE    = 150
CHUNK_OVERLAP = 25
MODELO        = "intfloat/multilingual-e5-large"

FILLER = set(['eh','ah','oh','mm','bueno','pues','entonces','osea','nada','tal',
              'digamos','venga','vale','claro','oye','mira','vamos','no','si',
              'aqui','ahi','eso','esto','asi','bien','muy','mas','ya','lo','la'])

def normalizar(texto):
    return unidecode(texto.lower())

def limpiar_filler(texto):
    palabras = texto.split()
    return ' '.join(p for p in palabras if p not in FILLER)

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
    return re.sub(r'\s+', ' ', texto_final).strip()

def hacer_chunks(texto_original, meta_base):
    titulo = meta_base.get('titulo', '')
    titulo_norm = normalizar(titulo)
    palabras = texto_original.split()
    chunks = []
    i = 0
    chunk_num = 0
    while i < len(palabras):
        segmento = ' '.join(palabras[i:i + CHUNK_SIZE])
        if len(segmento.strip()) > 40:
            # e5-large protocol: prefijo "passage: " + título + contenido normalizado
            segmento_norm = limpiar_filler(normalizar(segmento))
            texto_embed = f"passage: {titulo_norm} {segmento_norm}"
            meta = dict(meta_base)
            meta['chunk'] = chunk_num
            chunks.append({
                'texto_embed': texto_embed,
                'texto_display': segmento,   # texto original para mostrar
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
print("PASO 1: Borrando coleccion anterior...")
client = chromadb.PersistentClient(path=CHROMA_PATH)
try:
    client.delete_collection(COLECCION)
    print("Borrada.")
except:
    print("No existia.")

print("\nPASO 2: Cargando multilingual-e5-large...")
# Usar CUDA si disponible (RTX 4070)
try:
    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
except:
    device = 'cpu'
print(f"  Device: {device}")
modelo = SentenceTransformer(MODELO, device=device)
print(f"  OK — {modelo.get_sentence_embedding_dimension()} dims")

col = client.get_or_create_collection(
    COLECCION,
    metadata={"hnsw:space": "cosine"}
)

print(f"\nPASO 3: Procesando VTTs...")
archivos_vtt = sorted([f for f in os.listdir(VTT_DIR)
                       if f.endswith('.vtt') and not f.endswith('.info.json')])

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
            print(f"   [{i+1}/{len(archivos_vtt)}] chunks acumulados: {len(todos_chunks)}")
    except Exception as e:
        errores += 1
        print(f"   ERROR {archivo[:50]}: {e}")

print(f"\nTotal chunks: {len(todos_chunks)} | Errores: {errores}")
print("\n--- MUESTRA ---")
print("DISPLAY:", todos_chunks[0]['texto_display'][:150])
print("EMBED:  ", todos_chunks[0]['texto_embed'][:150])
print("---------------\n")

print("PASO 4: Indexando (e5-large es mas lento, paciencia)...")
LOTE = 64  # lote mas pequeño para e5-large
total = len(todos_chunks)

for inicio in range(0, total, LOTE):
    fin = min(inicio + LOTE, total)
    lote = todos_chunks[inicio:fin]
    textos_embed   = [c['texto_embed']   for c in lote]
    textos_display = [c['texto_display'] for c in lote]
    metas          = [c['meta']          for c in lote]
    ids = [f"{c['meta']['video_id']}_e5_c{c['meta']['chunk']}_{inicio}" for c in lote]
    embeddings = modelo.encode(textos_embed, show_progress_bar=False,
                               normalize_embeddings=True).tolist()
    col.add(documents=textos_display, embeddings=embeddings, metadatas=metas, ids=ids)
    pct = int((fin / total) * 100)
    if fin % 1000 == 0 or fin == total:
        print(f"   [{pct:3d}%] {fin}/{total}")

print(f"\nCOMPLETADO: {col.count()} chunks indexados con e5-large")
