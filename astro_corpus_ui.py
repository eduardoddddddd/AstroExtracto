"""
astro_corpus_ui.py  v4
----------------------
- Startup self-check integrado: valida BD, modelo y retrieval al arrancar
- normalize_embeddings=True en TODOS los encode (query e indexado)
- get_collection en lugar de get_or_create_collection
- Puerto fijo 7860
"""

import subprocess, json, os, re, glob, sqlite3, sys
from pathlib import Path
import gradio as gr
from unidecode import unidecode

_chroma_col = None
_modelo     = None

DIRECTORIO   = "C:/Users/Edu/Downloads/corpus_astro"
DB_PATH      = "C:/Users/Edu/Downloads/astro_knowledge.db"
CHROMA_PATH  = "C:/Users/Edu/Downloads/chroma_db"
MODELO_NAME  = "intfloat/multilingual-e5-large"
CHUNK_SIZE   = 500
CHUNK_OVERLAP= 50
LM_STUDIO    = "http://127.0.0.1:1234/v1/chat/completions"
LM_MODEL     = "qwen3-coder-30b-a3b-instruct"
RAG_TOP_K    = 8
PORT         = 7860


# ═══════════════════════════════════════════════════════════
#  STARTUP SELF-CHECK
# ═══════════════════════════════════════════════════════════
def startup_check():
    """Valida BD, modelo y retrieval al arrancar. Aborta si algo falla."""
    print("\n" + "═"*60)
    print("  ASTRO CORPUS v4 — SELF-CHECK DE INICIO")
    print("═"*60)
    ok = True

    # 1. ChromaDB
    try:
        import chromadb
        col = chromadb.PersistentClient(path=CHROMA_PATH).get_collection("astro_corpus")
        n = col.count()
        meta = col.metadata or {}
        espacio = meta.get("hnsw:space", "NO DEFINIDO")
        print(f"  [OK] ChromaDB: {n} chunks  |  hnsw:space={espacio}")
    except Exception as ex:
        print(f"  [FAIL] ChromaDB: {ex}")
        ok = False

    # 2. Modelo
    try:
        from sentence_transformers import SentenceTransformer
        modelo = SentenceTransformer(MODELO_NAME)
        dim_test = len(modelo.encode(["test"], normalize_embeddings=True)[0])
        print(f"  [OK] Modelo: {MODELO_NAME}  |  dim={dim_test}")
        if dim_test != 1024:
            print(f"  [WARN] Dimension esperada 1024, obtenida {dim_test} — mismatch con BD!")
            ok = False
    except Exception as ex:
        print(f"  [FAIL] Modelo: {ex}")
        ok = False

    # 3. Test de retrieval real
    if ok:
        try:
            q = "query: jupiter en casa 2 abundancia dinero recursos"
            emb = modelo.encode([q], normalize_embeddings=True).tolist()
            res = col.query(query_embeddings=emb, n_results=3)
            titulos = [m.get("titulo","?")[:50] for m in res["metadatas"][0]]
            print(f"  [OK] Retrieval test: top-3 resultados:")
            for i, t in enumerate(titulos, 1):
                print(f"       {i}. {t}")
        except Exception as ex:
            print(f"  [FAIL] Retrieval test: {ex}")
            ok = False

    print("═"*60)
    if not ok:
        print("  ABORTAR: corrige los errores arriba antes de continuar.")
        sys.exit(1)
    print("  TODO OK — arrancando interfaz en http://localhost:7860")
    print("═"*60 + "\n")



# ═══════════════════════════════════════════════════════════
#  HELPERS COMPARTIDOS
# ═══════════════════════════════════════════════════════════
def limpiar_vtt(texto):
    texto = re.sub(r"WEBVTT.*?\n", "", texto)
    texto = re.sub(r"\d{2}:\d{2}:\d{2}[\.,]\d+ --> \d{2}:\d{2}:\d{2}[\.,]\d+.*?\n", "", texto)
    texto = re.sub(r"^\d+\s*$", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"align:\w+.*", "", texto)
    texto = re.sub(r"\n{2,}", " ", texto)
    texto = re.sub(r" {2,}", " ", texto)
    return texto.strip()

def chunker(texto):
    chunks, i = [], 0
    while i < len(texto):
        chunks.append(texto[i:i+CHUNK_SIZE])
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

FILLER_QUERY = set(['eh','ah','oh','mm','bueno','pues','entonces','osea','nada',
                    'tal','digamos','venga','vale','claro','oye','mira','vamos'])

def normalizar_query(texto):
    texto = unidecode(texto.lower())
    palabras = [p for p in texto.split() if p not in FILLER_QUERY]
    return 'query: ' + ' '.join(palabras)

def init_sqlite():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY, canal TEXT, titulo TEXT,
        fecha TEXT, descripcion TEXT, url TEXT, srt_path TEXT)""")
    con.commit()
    return con

def get_col():
    global _chroma_col
    if _chroma_col is None:
        import chromadb
        # get_collection (sin or_create) para no recrear con metadata incorrecto
        _chroma_col = chromadb.PersistentClient(path=CHROMA_PATH).get_collection("astro_corpus")
    return _chroma_col

def get_modelo():
    global _modelo
    if _modelo is None:
        from sentence_transformers import SentenceTransformer
        _modelo = SentenceTransformer(MODELO_NAME)
    return _modelo

def encontrar_json(sub_path):
    p = re.sub(r"\.(es|en|auto)\.(vtt|srt)$", ".info.json", sub_path)
    p = re.sub(r"\.(vtt|srt)$", ".info.json", p)
    return p if os.path.exists(p) else None


# ═══════════════════════════════════════════════════════════
#  INDEXADO
# ═══════════════════════════════════════════════════════════
def _indexar_carpeta(directorio, log_fn):
    sub_files = list(set(
        glob.glob(f"{directorio}/**/*.vtt", recursive=True) +
        glob.glob(f"{directorio}/**/*.srt", recursive=True)
    ))
    yield log_fn(f"  📂  {len(sub_files)} archivos de subtítulos encontrados")

    try:
        modelo = get_modelo()
        col    = get_col()
        con    = init_sqlite()
    except Exception as ex:
        yield log_fn(f"  ❌  Error cargando modelo/BD: {ex}")
        return

    yield log_fn("  ✓  Modelo listo")
    ok = err = skip = 0

    for idx, sub_path in enumerate(sub_files):
        json_path = encontrar_json(sub_path)
        if not json_path:
            skip += 1
            continue
        try:
            meta  = json.loads(Path(json_path).read_text(encoding="utf-8"))
            texto = limpiar_vtt(Path(sub_path).read_text(encoding="utf-8"))
            if len(texto) < 300:  # Shorts y videos muy cortos tienen poco texto
                skip += 1
                continue
            con.execute("INSERT OR IGNORE INTO videos VALUES (?,?,?,?,?,?,?)", (
                meta.get("id"), meta.get("channel"), meta.get("title"),
                meta.get("upload_date"), (meta.get("description") or "")[:500],
                meta.get("webpage_url"), sub_path))
            con.commit()
            chunks = chunker(texto)
            # normalize_embeddings=True para consistencia con retrieval
            embs = modelo.encode(chunks, normalize_embeddings=True).tolist()
            vid  = meta["id"]
            col.add(
                documents=chunks, embeddings=embs,
                ids=[f"{vid}_{j}" for j in range(len(chunks))],
                metadatas=[{"video_id": vid, "titulo": meta.get("title",""),
                            "canal": meta.get("channel",""), "chunk": j,
                            "url": meta.get("webpage_url","")} for j in range(len(chunks))])
            ok += 1
            yield log_fn(f"  ✓  [{idx+1}/{len(sub_files)}] {(meta.get('title') or '')[:60]}")
        except Exception as ex:
            err += 1
            yield log_fn(f"  ❌  {Path(sub_path).name[:50]}: {ex}")

    total = con.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    con.close()
    yield log_fn(f"\n{'═'*55}\n✅  COMPLETADO  —  Total BD: {total} vídeos")
    yield log_fn(f"   Indexados: {ok}   Saltados: {skip}   Errores: {err}\n{'═'*55}")


def procesar(urls_texto):
    urls = [u.strip() for u in urls_texto.strip().splitlines() if u.strip()]
    if not urls:
        yield "⚠️  Añade al menos una URL."
        return
    os.makedirs(DIRECTORIO, exist_ok=True)
    log = ""
    def e(msg):
        nonlocal log
        log += msg + "\n"
        return log
    yield e(f"🚀  {len(urls)} canal(es)\n{'─'*55}")
    for i, url in enumerate(urls, 1):
        yield e(f"\n📡  [{i}/{len(urls)}] {url}")
        cmd = ["yt-dlp","--skip-download","--write-auto-subs","--sub-lang","es",
               "--write-info-json","--ignore-errors","--newline",
               "--match-filter", "duration > 60",
               "--output", f"{DIRECTORIO}/%(channel)s/%(upload_date)s_%(id)s_%(title)s.%(ext)s", url]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        for linea in proc.stdout:
            linea = linea.rstrip()
            if linea and any(k in linea for k in ["[download]","[info]","Writing","Subtitle","ERROR","WARNING"]):
                yield e(f"  {linea}")
        proc.wait()
        yield e(f"  ✓  Descarga {i} completada")
    yield e(f"\n🗄️  Indexando...\n{'─'*55}")
    yield e("  ⏳  Cargando modelo de embeddings...")
    for estado in _indexar_carpeta(DIRECTORIO, e):
        yield estado

def reindexar():
    log = ""
    def e(msg):
        nonlocal log
        log += msg + "\n"
        return log
    yield e(f"🔄  Reindexando: {DIRECTORIO}\n{'─'*55}")
    yield e("  ⏳  Cargando modelo...")
    for estado in _indexar_carpeta(DIRECTORIO, e):
        yield estado


# ═══════════════════════════════════════════════════════════
#  BÚSQUEDA SEMÁNTICA (pestaña Consultar)
# ═══════════════════════════════════════════════════════════
def consultar(pregunta, n):
    if not pregunta.strip():
        return "⚠️  Escribe algo primero."
    try:
        modelo = get_modelo()
        col    = get_col()
    except Exception as ex:
        return f"❌  {ex}"
    pregunta_norm = normalizar_query(pregunta)
    # normalize_embeddings=True OBLIGATORIO para e5-large
    emb = modelo.encode([pregunta_norm], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=emb, n_results=int(n))
    if not res["documents"][0]:
        return "Sin resultados. ¿Has indexado algún canal?"
    out = f"🔍  «{pregunta}»\n{'═'*60}\n\n"
    for i, (doc, meta) in enumerate(zip(res["documents"][0], res["metadatas"][0]), 1):
        out += f"── Resultado {i} {'─'*40}\n"
        out += f"   Canal : {meta.get('canal','?')}\n"
        out += f"   Vídeo : {meta.get('titulo','?')[:70]}\n"
        if meta.get("url"):
            out += f"   URL   : {meta['url']}\n"
        out += f"\n{doc[:450]}\n\n"
    return out


# ═══════════════════════════════════════════════════════════
#  RAG COMPLETO (pestaña Preguntar a Qwen)
# ═══════════════════════════════════════════════════════════
def rag_consultar(pregunta, top_k):
    if not pregunta.strip():
        yield "Escribe una pregunta primero."
        return
    try:
        modelo = get_modelo()
        col    = get_col()
    except Exception as ex:
        yield f"Error cargando modelo: {ex}"
        return

    yield "Buscando fragmentos relevantes..."
    q_norm = normalizar_query(pregunta)
    # normalize_embeddings=True OBLIGATORIO para e5-large
    emb = modelo.encode([q_norm], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=emb, n_results=int(top_k) + 4)
    docs_raw  = res["documents"][0]
    metas_raw = res["metadatas"][0]

    pares = [(d, m) for d, m in zip(docs_raw, metas_raw) if len(d.strip()) >= 150]
    pares = pares[:int(top_k)]

    if not pares:
        yield "Sin resultados útiles en el corpus."
        return

    contexto = ""
    fuentes  = []
    vistos   = set()
    for i, (doc, meta) in enumerate(pares, 1):
        titulo = meta.get("titulo", "?")[:70]
        contexto += f"\n[{i}. {titulo}]\n{doc}\n"
        url = meta.get("url", "")
        clave = titulo[:50]
        if clave not in vistos:
            vistos.add(clave)
            entrada = f"  {len(vistos)}. {titulo}"
            if url:
                entrada += f"\n     {url}"
            fuentes.append(entrada)

    prompt = f"""Eres un asistente experto en astrología terapéutica y evolutiva basado en las enseñanzas de Isabel Pareja.

Tu tarea: responder la pregunta del usuario usando el contenido de los fragmentos de transcripción que se te dan.

INSTRUCCIONES:
- Lee cada fragmento completo y extrae toda la información relevante que contenga.
- Sintetiza lo que Isabel Pareja dice sobre el tema en cuestión.
- Si varios fragmentos hablan de lo mismo, integra la información.
- Si algún fragmento no es relevante para la pregunta, ignóralo.
- Responde en español, de forma clara y directa.
- No menciones los números de fragmento en tu respuesta.
- Si genuinamente no hay información sobre el tema, dilo en una sola frase.

FRAGMENTOS DE TRANSCRIPCIÓN:
{contexto}

PREGUNTA: {pregunta}

RESPUESTA:"""

    yield f"Consultando {LM_MODEL} ({len(pares)} fragmentos)...\n"

    try:
        import urllib.request as ur
        payload = json.dumps({
            "model": LM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.35,
            "max_tokens": 1500,
            "stream": False
        }).encode("utf-8")
        req = ur.Request(LM_STUDIO, data=payload, headers={"Content-Type": "application/json"})
        with ur.urlopen(req, timeout=240) as resp:
            data = json.loads(resp.read())
        respuesta = data["choices"][0]["message"]["content"].strip()
    except Exception as ex:
        yield f"Error LM Studio: {ex}\n\nAsegúrate de que LM Studio está arrancado en {LM_STUDIO}"
        return

    separador = "=" * 60
    linea     = "─" * 60
    salida = f"PREGUNTA: {pregunta}\n{separador}\n\n{respuesta}\n\n{linea}\nFUENTES CONSULTADAS:\n" + "\n".join(fuentes)
    yield salida


# ═══════════════════════════════════════════════════════════
#  ESTADO
# ═══════════════════════════════════════════════════════════
def estado():
    try:
        con     = sqlite3.connect(DB_PATH)
        total   = con.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        canales = con.execute("SELECT canal, COUNT(*) c FROM videos GROUP BY canal ORDER BY c DESC").fetchall()
        con.close()
        chunks = get_col().count()
        out  = f"📊  Base de conocimiento\n{'─'*40}\n"
        out += f"  Vídeos   : {total}\n  Chunks   : {chunks}\n\n  Por canal:\n"
        for c, n in canales:
            out += f"    • {c or 'desconocido'}: {n} vídeos\n"
        return out
    except Exception as ex:
        return f"Error: {ex}\nUsa 'Reindexar' primero si la BD está vacía."


# ═══════════════════════════════════════════════════════════
#  INTERFAZ GRADIO
# ═══════════════════════════════════════════════════════════
CSS = """
.log textarea {
    font-family: 'Courier New', monospace !important;
    font-size: 12px !important;
    background: #0d1117 !important;
    color: #3fb950 !important;
}
"""

with gr.Blocks(title="🪐 Astro Corpus", theme=gr.themes.Base(), css=CSS) as app:
    gr.Markdown("# 🪐 Astro Corpus\nBase de conocimiento astrológico personal")
    with gr.Tabs():
        with gr.Tab("📡 Ingestar canales"):
            gr.Markdown("Una URL por línea.")
            urls = gr.Textbox(label="URLs", lines=4,
                              placeholder="https://www.youtube.com/@canal_astrologia/videos")
            with gr.Row():
                btn1 = gr.Button("▶  Descargar e indexar", variant="primary")
                btn2 = gr.Button("🔄  Reindexar lo ya descargado", variant="secondary")
            log  = gr.Textbox(label="Actividad", lines=22, interactive=False, elem_classes="log")
            btn1.click(fn=procesar,  inputs=urls, outputs=log)
            btn2.click(fn=reindexar, inputs=[],   outputs=log)
        with gr.Tab("🔍 Consultar"):
            gr.Markdown("Búsqueda semántica directa (sin LLM).")
            with gr.Row():
                q = gr.Textbox(label="Consulta", scale=4,
                               placeholder="Luna Saturno restricción emocional")
                n = gr.Slider(1, 10, value=5, step=1, label="Resultados")
            btn3 = gr.Button("Buscar", variant="primary")
            res  = gr.Textbox(label="Resultados", lines=20, interactive=False)
            btn3.click(fn=consultar, inputs=[q, n], outputs=res)
        with gr.Tab("💬 Preguntar a Qwen"):
            gr.Markdown("RAG completo: recupera fragmentos + genera respuesta con Qwen via LM Studio.")
            with gr.Row():
                rq = gr.Textbox(label="Pregunta", scale=4,
                                placeholder="Que dice Isabel Pareja sobre Saturno en casa 7?")
                rk = gr.Slider(3, 10, value=8, step=1, label="Fragmentos a recuperar")
            btn_rag = gr.Button("Preguntar", variant="primary")
            rag_out = gr.Textbox(label="Respuesta", lines=22, interactive=False)
            btn_rag.click(fn=rag_consultar, inputs=[rq, rk], outputs=rag_out)
        with gr.Tab("📊 Estado"):
            btn4 = gr.Button("🔄 Actualizar")
            est  = gr.Textbox(label="Estado", lines=14, interactive=False)
            btn4.click(fn=estado, outputs=est)
            app.load(fn=estado, outputs=est)


# ═══════════════════════════════════════════════════════════
#  MAIN — self-check antes de arrancar
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    startup_check()  # aborta si algo falla
    app.launch(server_port=PORT, server_name="127.0.0.1", inbrowser=True)
