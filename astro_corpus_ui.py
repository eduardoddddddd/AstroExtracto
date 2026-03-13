"""
astro_corpus_ui.py  v3
----------------------
Soporte VTT y SRT. Streaming real con Popen.
Sin gr.Progress (causa crash). Boton reindexar.

    pip install yt-dlp chromadb sentence-transformers gradio
    python astro_corpus_ui.py
"""

import subprocess, json, os, re, glob, sqlite3
from pathlib import Path
import gradio as gr

_chroma_col = None
_modelo     = None

DIRECTORIO   = "C:/Users/Edu/Downloads/corpus_astro"
DB_PATH      = "C:/Users/Edu/Downloads/astro_knowledge.db"
CHROMA_PATH  = "C:/Users/Edu/Downloads/chroma_db"
MODELO_NAME  = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE   = 500
CHUNK_OVERLAP= 50


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
        _chroma_col = chromadb.PersistentClient(path=CHROMA_PATH).get_or_create_collection("astro_corpus")
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


def _indexar_carpeta(directorio, log_fn):
    """Indexa todos los VTT/SRT de una carpeta. log_fn(msg) -> str acumulado."""
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
        yield log_fn(f"  ❌  Error cargando modelo: {ex}")
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
            if len(texto) < 100:
                skip += 1
                continue
            con.execute("INSERT OR IGNORE INTO videos VALUES (?,?,?,?,?,?,?)", (
                meta.get("id"), meta.get("channel"), meta.get("title"),
                meta.get("upload_date"), (meta.get("description") or "")[:500],
                meta.get("webpage_url"), sub_path))
            con.commit()
            chunks = chunker(texto)
            embs   = modelo.encode(chunks).tolist()
            vid    = meta["id"]
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

def consultar(pregunta, n):
    if not pregunta.strip():
        return "⚠️  Escribe algo primero."
    try:
        modelo = get_modelo()
        col    = get_col()
    except Exception as ex:
        return f"❌  {ex}"
    res = col.query(query_embeddings=modelo.encode([pregunta]).tolist(), n_results=int(n))
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
    except Exception:
        return "Base de datos vacía. Usa 'Reindexar' primero."


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
            btn1.click(fn=procesar,   inputs=urls, outputs=log)
            btn2.click(fn=reindexar,  inputs=[],   outputs=log)
        with gr.Tab("🔍 Consultar"):
            gr.Markdown("Búsqueda semántica.")
            with gr.Row():
                q = gr.Textbox(label="Consulta", scale=4,
                               placeholder="Luna Saturno restricción emocional")
                n = gr.Slider(1, 10, value=5, step=1, label="Resultados")
            btn3 = gr.Button("Buscar", variant="primary")
            res  = gr.Textbox(label="Resultados", lines=20, interactive=False)
            btn3.click(fn=consultar, inputs=[q, n], outputs=res)
        with gr.Tab("📊 Estado"):
            btn4 = gr.Button("🔄 Actualizar")
            est  = gr.Textbox(label="Estado", lines=14, interactive=False)
            btn4.click(fn=estado, outputs=est)
            app.load(fn=estado, outputs=est)

if __name__ == "__main__":
    print("\nAstro Corpus v3 arrancando en http://localhost:7860\n")
    app.launch(server_port=7860, inbrowser=True)

