"""
rag_query.py — RAG completo: ChromaDB (e5-large) + LM Studio (Qwen)
====================================================================
Flujo:
  pregunta → normalizar → embedding e5-large → ChromaDB top-k chunks
           → prompt con contexto → LM Studio /v1/chat/completions → respuesta

USO: python rag_query.py "¿Qué dice Isabel Pareja sobre Júpiter en casa 2?"
"""

import sys, json
sys.stdout.reconfigure(encoding='utf-8')

import chromadb
from sentence_transformers import SentenceTransformer
from unidecode import unidecode
import urllib.request

CHROMA_PATH  = "C:/Users/Edu/Downloads/chroma_db"
COLECCION    = "astro_corpus"
MODELO_EMB   = "intfloat/multilingual-e5-large"
LM_STUDIO    = "http://127.0.0.1:1234/v1/chat/completions"
LM_MODEL     = "qwen3-coder-30b-a3b-instruct"
TOP_K        = 6

FILLER = set(['eh','ah','oh','mm','bueno','pues','entonces','osea','nada','tal',
              'digamos','venga','vale','claro','oye','mira','vamos'])

def normalizar(texto):
    t = unidecode(texto.lower())
    return 'query: ' + ' '.join(p for p in t.split() if p not in FILLER)

def recuperar(pregunta, k=TOP_K):
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col    = client.get_collection(COLECCION)
    modelo = SentenceTransformer(MODELO_EMB)
    emb    = modelo.encode([normalizar(pregunta)], normalize_embeddings=True).tolist()
    res    = col.query(query_embeddings=emb, n_results=k)
    chunks = []
    for doc, meta in zip(res['documents'][0], res['metadatas'][0]):
        chunks.append({'texto': doc, 'titulo': meta.get('titulo','?'), 'url': meta.get('url','')})
    return chunks

def construir_prompt(pregunta, chunks):
    contexto = ""
    for i, c in enumerate(chunks, 1):
        contexto += f"\n[Fragmento {i} — {c['titulo'][:60]}]\n{c['texto']}\n"

    return f"""Eres un asistente especializado en astrología terapéutica y evolutiva, basado en las enseñanzas de Isabel Pareja.

Responde la siguiente pregunta usando ÚNICAMENTE la información de los fragmentos proporcionados.
Si los fragmentos no contienen información suficiente, dilo claramente.
Responde siempre en español. Sé conciso y directo. No inventes ni extrapoles.

FRAGMENTOS DEL CORPUS:
{contexto}

PREGUNTA: {pregunta}

RESPUESTA:"""

def preguntar_lmstudio(prompt, stream=False):
    payload = json.dumps({
        "model": LM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 800,
        "stream": False
    }).encode('utf-8')

    req = urllib.request.Request(
        LM_STUDIO,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data['choices'][0]['message']['content'].strip()

def rag(pregunta, verbose=False):
    if verbose:
        print(f"\nRecuperando chunks para: {pregunta}")
    chunks = recuperar(pregunta)
    if verbose:
        for i, c in enumerate(chunks, 1):
            print(f"  [{i}] {c['titulo'][:70]}")
    prompt = construir_prompt(pregunta, chunks)
    if verbose:
        print(f"\nConsultando {LM_MODEL}...")
    respuesta = preguntar_lmstudio(prompt)
    return respuesta, chunks

if __name__ == "__main__":
    pregunta = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else "¿Qué dice Isabel Pareja sobre Júpiter en casa 2?"
    respuesta, chunks = rag(pregunta, verbose=True)
    print(f"\n{'='*60}")
    print(f"PREGUNTA: {pregunta}")
    print(f"{'='*60}")
    print(respuesta)
    print(f"\nFuentes:")
    for c in chunks:
        print(f"  - {c['titulo'][:70]}")
        if c['url']:
            print(f"    {c['url']}")
