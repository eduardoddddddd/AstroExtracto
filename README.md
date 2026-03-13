# 🪐 AstroExtracto

> Base de conocimiento astrológico personal construida desde canales de YouTube en castellano, con búsqueda semántica RAG y consultas en lenguaje natural vía LLM local.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Gradio](https://img.shields.io/badge/Interface-Gradio-orange)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-purple)
![e5-large](https://img.shields.io/badge/Embeddings-e5--large--1024d-blueviolet)
![Status](https://img.shields.io/badge/Status-v4%20estable-brightgreen)

---

## 📖 Descripción

AstroExtracto es una herramienta **100% local** que permite construir una base de conocimiento astrológico personal a partir de transcripciones de canales de YouTube seleccionados por el usuario.

Dado un corpus de decenas o cientos de horas de contenido, permite consultar ese conocimiento acumulado por **significado semántico**, no por palabras clave exactas. Una pregunta como *"¿qué dice Isabel Pareja sobre Júpiter en casa 2?"* localiza los fragmentos exactos aunque el astrólogo no haya usado esas palabras literales.

---

## ✨ Características (v4)

| Característica | Detalle |
|---|---|
| 📥 Descarga masiva | `yt-dlp` descarga subtítulos sin bajar el vídeo |
| 📄 Soporte VTT y SRT | Sin dependencia de `ffmpeg` |
| 🗄️ Base vectorial local | ChromaDB persistente, sin datos en la nube |
| 🔍 Búsqueda semántica | `multilingual-e5-large` (1024 dims, estado del arte multilingüe) |
| 🖥️ Interfaz visual | Gradio en `http://localhost:7860` |
| 🤖 RAG con LLM local | Pipeline completo con Qwen via LM Studio |
| 🔬 Startup self-check | Valida BD + modelo + retrieval real al arrancar |
| 📊 SQLite metadatos | Trazabilidad completa: canal, vídeo, URL, fecha |


---

## 🏗️ Arquitectura (v4)

```
YouTube Channels (URLs seleccionadas por el usuario)
          │
          ▼
    ┌─────────────┐
    │   yt-dlp    │  ← descarga subtítulos (.vtt/.srt) + metadatos (.json)
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Limpieza   │  ← elimina timestamps, tags HTML, ruido VTT/SRT
    └──────┬──────┘
           │
     ┌─────┴──────┐
     │            │
     ▼            ▼
┌─────────┐  ┌──────────────────────────────────────────┐
│ SQLite  │  │              ChromaDB                    │
│ videos  │  │   colección: astro_corpus                │
│ metad.  │  │   hnsw:space = cosine                    │
└─────────┘  │   chunks ~500 chars, overlap 50          │
             │   embeddings: e5-large 1024 dims          │
             │   prefijo indexado: "passage: título+txt" │
             └──────────────┬───────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │     Consulta del usuario    │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  multilingual-e5-large      │
              │  normalizar_query()         │  ← prefijo "query: " + unidecode
              │  normalize_embeddings=True  │  ← OBLIGATORIO para e5
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  ChromaDB query             │
              │  top_k + 4 candidatos       │
              │  filtro chunks < 150 chars  │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  LM Studio — Qwen           │
              │  RAG: contexto + pregunta   │  ← 127.0.0.1:1234
              │  → respuesta con fuentes    │
              └────────────────────────────┘
```

### Stack tecnológico

| Capa | Tecnología | Notas |
|---|---|---|
| Descarga | `yt-dlp` | Sin API key, activamente mantenido |
| Interfaz | `Gradio` | Web local, streaming de logs |
| Embeddings | `intfloat/multilingual-e5-large` | 1024 dims, superior a MiniLM para castellano |
| Vector DB | `ChromaDB` | Persistente, local, espacio coseno |
| Metadatos | `SQLite` | Sin servidor, portable |
| LLM (RAG) | `Qwen3-coder-30b` via `LM Studio` | 100% local, sin API keys |


---

## 🚀 Instalación rápida

### Requisitos

- Python 3.9–3.12 (no 3.14 — sin wheels CUDA para PyTorch)
- ~3 GB disco para el modelo e5-large
- LM Studio corriendo en `http://127.0.0.1:1234` con modelo Qwen cargado

### Pasos

```bash
git clone https://github.com/eduardoddddddd/AstroExtracto.git
cd AstroExtracto
pip install -r requirements.txt
python astro_corpus_ui.py
```

La interfaz se abre en `http://localhost:7860`. Antes de abrir el navegador verás el **self-check** en consola (ver sección más abajo).

### `requirements.txt`

```
yt-dlp>=2024.1.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
gradio>=4.0.0
unidecode>=1.3.0
```

---

## 🔬 Self-check de inicio (v4)

Al arrancar, el script valida automáticamente el entorno **antes** de abrir la interfaz:

```
════════════════════════════════════════════════════════════
  ASTRO CORPUS v4 — SELF-CHECK DE INICIO
════════════════════════════════════════════════════════════
  [OK] ChromaDB: 10363 chunks  |  hnsw:space=cosine
  [OK] Modelo: intfloat/multilingual-e5-large  |  dim=1024
  [OK] Retrieval test: top-3 resultados:
       1. Abundancia emocional y material: Júpiter en tu Casa 2
       2. Los planetas en casa 2: recursos y valores
       3. Conjunción Júpiter-Venus: expansión material
════════════════════════════════════════════════════════════
  TODO OK — arrancando interfaz en http://localhost:7860
════════════════════════════════════════════════════════════
```

Si algo falla (dimensión incorrecta, colección inexistente, retrieval erróneo), **el proceso aborta con un mensaje claro** antes de mostrar la interfaz.

Los tres checks son:
1. **ChromaDB** — verifica chunks, colección y espacio de distancia
2. **Modelo** — carga e5-large y verifica que produce vectores de 1024 dims
3. **Retrieval real** — hace una query de prueba y muestra los top-3 títulos


---

## 📋 Uso

### 1. Ingestar canales

Pestaña **📡 Ingestar canales** → introduce URLs → **▶ Descargar e indexar**

Formatos válidos:
```
https://www.youtube.com/@NombreCanal/videos
https://www.youtube.com/playlist?list=PLxxxx
https://www.youtube.com/watch?v=VIDEO_ID
```

Si ya tienes los VTTs descargados: botón **🔄 Reindexar lo ya descargado**.

### 2. Búsqueda semántica directa

Pestaña **🔍 Consultar** — retrieval puro sin LLM. Ideal para verificar que los chunks correctos se recuperan antes de pasar al RAG.

Ejemplos:
```
Jupiter casa 2 abundancia dinero
Saturno Neptuno conjuncion 2026
Luna casa 12 emociones ocultas
nodo norte mision de vida
```

> 💡 La búsqueda es semántica. "restricción afectiva Saturno-Luna" encuentra
> fragmentos sobre "el bloqueo emocional de Saturno en aspecto a la Luna".

### 3. RAG completo con Qwen

Pestaña **💬 Preguntar a Qwen** — recupera fragmentos + genera respuesta sintetizada.

Requiere LM Studio activo en `http://127.0.0.1:1234` con modelo `qwen3-coder-30b-a3b-instruct`.

### 4. Estado de la BD

Pestaña **📊 Estado** — muestra total de vídeos, chunks y desglose por canal.

---

## ⚙️ Configuración

Variables en la cabecera de `astro_corpus_ui.py`:

```python
DIRECTORIO   = "C:/Users/Edu/Downloads/corpus_astro"
DB_PATH      = "C:/Users/Edu/Downloads/astro_knowledge.db"
CHROMA_PATH  = "C:/Users/Edu/Downloads/chroma_db"
MODELO_NAME  = "intfloat/multilingual-e5-large"
CHUNK_SIZE   = 500     # caracteres por chunk
CHUNK_OVERLAP= 50      # solapamiento
LM_STUDIO    = "http://127.0.0.1:1234/v1/chat/completions"
LM_MODEL     = "qwen3-coder-30b-a3b-instruct"
RAG_TOP_K    = 8       # fragmentos a recuperar
PORT         = 7860    # fijo, sin acumulación de puertos
```


---

## 📜 Historial de versiones detallado

### v1 — Prototipo inicial (commit `a7aada3`)

**Objetivo:** MVP funcional: descargar VTTs e indexarlos.

**Lo que se hizo:**
- Descarga masiva con `yt-dlp` (subtítulos + metadatos JSON)
- Limpieza básica de archivos VTT (timestamps, tags HTML)
- Indexación en ChromaDB con `paraphrase-multilingual-MiniLM-L12-v2` (384 dims)
- Interfaz Gradio con 3 pestañas: Ingestar, Consultar, Estado
- SQLite para metadatos de vídeos

**Problemas detectados:**
- El texto de los VTTs llegaba **triplicado** — la misma frase aparecía repetida 3 veces consecutivas porque los subtítulos automáticos de YouTube solapan frases para animar el texto
- 46.289 chunks indexados, pero más de 2/3 eran duplicados ruidosos
- Sin normalización de texto: tildes, mayúsculas y palabras de relleno interferían con la relevancia

**Conclusión:** La calidad del retrieval era baja porque el corpus estaba contaminado. Necesario limpiar antes de indexar.

---

### v2 — Limpieza y normalización (commits `5f1a2c6`, `1be79a0`)

**Objetivo:** Corpus limpio + mejor relevancia de búsqueda.

**Lo que se hizo:**
- Reescritura del parser VTT para eliminar duplicados: deduplica líneas consecutivas idénticas
- Normalización de queries: `unidecode` (elimina tildes) + lowercase + filtro de palabras de relleno ("bueno", "pues", "entonces"...)
- Reducción de chunk size a 120 palabras para mayor precisión
- Script independiente `reindex_v2.py` para reindexar desde cero

**Resultado:** 12.918 chunks limpios vs 46.289 ruidosos. El corpus bajó de tamaño pero ganó calidad.

**Problemas restantes:**
- MiniLM-L12-v2 (384 dims) tiene rendimiento mediocre en castellano técnico
- Las búsquedas encontraban fragmentos temáticamente relacionados pero no el vídeo específico correcto
- Ejemplo: query "Júpiter casa 2" devolvía vídeos sobre "conjunción Júpiter-Neptuno" en lugar del vídeo dedicado a Júpiter en Casa 2

**Conclusión:** El modelo era el cuello de botella. MiniLM es rápido pero no suficientemente preciso para terminología astrológica en castellano.

---

### v3 — Upgrade a e5-large + RAG completo (commits `c39c614`, `238d145`, `3e69807`)

**Objetivo:** Mejor modelo de embeddings + pipeline RAG funcional con LLM local.

**Lo que se hizo:**
- Cambio de modelo a `intfloat/multilingual-e5-large` (1024 dims, 560M parámetros)
- Protocolo e5: prefijo `"passage: "` al indexar, `"query: "` al buscar — **obligatorio** para este modelo
- `normalize_embeddings=True` en el retrieval (eval_e5.py) — **obligatorio** para e5
- Reindexado completo: 10.363 chunks con el nuevo modelo
- Pipeline RAG completo: retrieval → prompt estructurado → Qwen via LM Studio → respuesta con fuentes
- Filtro de chunks cortos (< 150 chars) para eliminar solapamientos truncados

**Problemas graves descubiertos en producción:**

**Bug 1 (crítico):** `consultar()` llamaba `encode()` **sin** `normalize_embeddings=True`. El código correcto estaba en `eval_e5.py` y en `rag_consultar()`, pero se perdió en la función de búsqueda directa. Resultado: el retrieval de la pestaña "Consultar" producía vectores en un espacio diferente al de la BD → resultados incorrectos.

**Bug 2 (crítico):** `get_col()` usaba `get_or_create_collection()` en lugar de `get_collection()`. Esto significa que si ChromaDB recreaba el objeto colección en una nueva sesión, podía hacerlo **sin** el metadato `hnsw:space: cosine`, cayendo a distancia euclidiana y rompiendo la similitud semántica.

**Bug 3 (menor):** `RAG_TOP_K = 6` — demasiado bajo. Con 6 fragmentos, la probabilidad de que el fragmento exacto entre los top-6 era insuficiente para queries específicas.

**Bug 4 (no detectado hasta v4):** `_indexar_carpeta()` llamaba `modelo.encode(chunks)` también **sin** `normalize_embeddings=True`. Los chunks indexados y los vectores de query estaban en espacios ligeramente distintos.

**Diagnóstico de los bugs:** Se detectaron ejecutando el check de diagnóstico directamente contra ChromaDB:
```
chromadb.errors.InvalidArgumentError:
Collection expecting embedding with dimension of 1024, got 384
```
Este error reveló que en algún punto del pipeline se estaba usando el modelo MiniLM (384 dims) en lugar de e5-large (1024 dims) — probablemente por un objeto `_modelo` cacheado de una sesión anterior.

**Conclusión:** Los fixes parciales aplicados en v3 no resolvieron el problema porque el bug de `_indexar_carpeta` seguía contaminando los índices. La solución real requería un self-check integrado que verificara el pipeline completo en cada inicio.


---

### v4 — Self-check integrado + corrección completa (commit `204885f`) ← **versión actual**

**Objetivo:** Eliminar todos los bugs de embeddings y hacer el sistema autodiagnósticable.

**Lo que se hizo:**

1. **`startup_check()` integrado en `main`** — ejecuta tres validaciones antes de abrir la interfaz:
   - Conecta a ChromaDB y verifica chunks + `hnsw:space`
   - Carga e5-large y verifica que produce vectores de exactamente 1024 dims
   - Hace una query de prueba real y muestra los top-3 títulos recuperados
   - Si cualquier check falla → `sys.exit(1)` con mensaje claro

2. **`normalize_embeddings=True` en los 4 sitios del código:**
   - `consultar()` — búsqueda directa (era el bug principal no resuelto en v3)
   - `rag_consultar()` — ya estaba correcto en v3, conservado
   - `_indexar_carpeta()` — **nuevo en v4**, el bug más silencioso
   - `startup_check()` — en el test de retrieval

3. **`get_collection()` en lugar de `get_or_create_collection()`** — evita recrear la colección con metadatos incorrectos

4. **`PORT = 7860` fijo** — elimina la acumulación en puertos 7861, 7862, 7863... causada por procesos anteriores que no se limpiaban

5. **Reescritura completa del archivo** — elimina inconsistencias acumuladas entre parches

**Verificación pre-deploy:**
```
  [OK] startup_check definida
  [OK] normalize x4 (4 ocurrencias de normalize_embeddings=True)
  [OK] normalize en indexar: encode(chunks, normalize_embeddings=True)
  [OK] get_collection sin or_create
  [OK] PORT=7860
  [OK] startup_check en main
```

**Cambios en la interfaz:**
- Puerto fijo 7860 (antes acumulaba: 7860→7861→7862→7863)
- Slider RAG por defecto: 8 fragmentos (antes 6)
- Pestaña "Preguntar a Qwen" con slider visible de fragmentos

**Lección aprendida:** Los bugs de embeddings son especialmente difíciles porque **no dan error en tiempo de ejecución** — el sistema devuelve resultados, pero incorrectos. La única forma de detectarlos es comparar dimensiones explícitamente o hacer un test de retrieval con ground truth conocido. Por eso el self-check es parte permanente del código, no un script externo.

---

## 🗂️ Scripts de utilidad (`scripts/`)

| Script | Propósito | Estado |
|---|---|---|
| `reindex_e5.py` | Reindexado completo con e5-large | ✅ Usar este |
| `check_chroma.py` | Diagnóstico rápido de la BD | ✅ |
| `check_chroma2.py` | Inspección de calidad con búsquedas de prueba | ✅ |
| `test_busqueda.py` | Validación post-reindexado | ✅ |
| `rag_query.py` | CLI standalone del pipeline RAG | ✅ |
| `reindex_limpio.py` | Reindexado v1 (obsoleto, MiniLM) | ⚠️ Histórico |
| `reindex_v2.py` | Reindexado v2 (obsoleto, MiniLM) | ⚠️ Histórico |
| `demo_embeddings.py` | Demo educativa similitud coseno | ℹ️ |

### Reindexar desde cero

Si necesitas reindexar (cambio de modelo, corpus nuevo):
```powershell
# 1. Hacer backup de la BD actual (opcional)
# 2. Eliminar la colección existente
python -c "import chromadb; chromadb.PersistentClient('C:/Users/Edu/Downloads/chroma_db').delete_collection('astro_corpus')"
# 3. Reindexar
python scripts/reindex_e5.py
```

> ⚠️ Tras reindexar con un modelo diferente, el startup_check verificará automáticamente
> que las dimensiones coinciden antes de arrancar la interfaz.


---

## 🧠 Detalles técnicos del pipeline de embeddings

### Por qué e5-large y no MiniLM

| Modelo | Dims | Parámetros | Castellano | Velocidad |
|---|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 118M | Aceptable | Rápido |
| `intfloat/multilingual-e5-large` | 1024 | 560M | Excelente | Medio |

e5-large fue entrenado específicamente con pares (query, passage) en múltiples idiomas. Para terminología técnica como la astrológica en castellano, la diferencia de calidad es significativa.

### El protocolo de prefijos e5

El modelo e5 **requiere** prefijos específicos para distinguir el tipo de texto:

```python
# Al INDEXAR cada chunk:
texto_a_indexar = "passage: " + titulo_normalizado + " " + texto_chunk

# Al BUSCAR:
query_a_buscar = "query: " + texto_normalizado_de_la_pregunta
```

Sin estos prefijos, el modelo no funciona correctamente aunque las dimensiones coincidan.

### Por qué `normalize_embeddings=True` es obligatorio

`e5-large` produce vectores que **deben** estar normalizados a longitud unitaria para que la similitud coseno funcione correctamente. Sin normalización, los vectores de diferentes longitudes producen rankings incorrectos.

```python
# MAL — puede dar resultados incorrectos con e5
emb = modelo.encode([texto]).tolist()

# BIEN — obligatorio para e5-large
emb = modelo.encode([texto], normalize_embeddings=True).tolist()
```

### Por qué `get_collection` y no `get_or_create_collection`

`get_or_create_collection` crea la colección si no existe. Si la crea en una sesión nueva, puede hacerlo sin el metadato `{"hnsw:space": "cosine"}` → la BD usa distancia euclidiana → el retrieval semántico falla silenciosamente.

`get_collection` lanza una excepción si la colección no existe, lo que es correcto — si no existe hay que reindexar explícitamente.

---

## 🗺️ Roadmap

### ✅ v1 — MVP (commit `a7aada3`)
- [x] Descarga masiva con yt-dlp
- [x] Soporte VTT nativo
- [x] ChromaDB + embeddings MiniLM
- [x] Interfaz Gradio básica

### ✅ v2 — Limpieza (commits `5f1a2c6`, `1be79a0`)
- [x] Deduplicación de texto VTT triplicado
- [x] Normalización: unidecode + lowercase + filtro fillers
- [x] Chunks más pequeños (120 palabras)

### ✅ v3 — e5-large + RAG (commits `c39c614`, `238d145`, `3e69807`)
- [x] Upgrade a multilingual-e5-large (1024 dims)
- [x] Protocolo de prefijos e5
- [x] Pipeline RAG completo con LM Studio / Qwen
- [x] Filtro de chunks cortos

### ✅ v4 — Self-check + corrección completa (commit `204885f`)
- [x] `startup_check()` integrado — valida BD + modelo + retrieval al inicio
- [x] `normalize_embeddings=True` en los 4 puntos del pipeline
- [x] `get_collection` en lugar de `get_or_create_collection`
- [x] Puerto fijo 7860
- [x] Reescritura limpia del archivo principal

### 🔄 v5 — Calidad de respuesta (pendiente)
- [ ] Cambio de modelo LLM: Qwen-coder → modelo de conversación general
- [ ] Reranking de fragmentos por relevancia (cross-encoder)
- [ ] Filtros en UI: por canal, por fecha de vídeo
- [ ] Deduplicación de fragmentos muy similares en el contexto RAG

### 🔮 v6 — Funcionalidades avanzadas
- [ ] Whisper para vídeos sin subtítulos automáticos
- [ ] Resumen automático por vídeo al indexar
- [ ] Clustering semántico de temas
- [ ] Comparativa de perspectivas entre astrólogos sobre un mismo tema
- [ ] Exportación de fragmentos a Markdown/PDF
- [ ] Soporte podcasts (MP3/RSS)


---

## 📁 Estructura del proyecto

```
AstroExtracto/
├── astro_corpus_ui.py      ← aplicación principal (Gradio) — v4
├── requirements.txt        ← dependencias Python
├── README.md               ← este archivo
├── .gitignore              ← excluye corpus, BD y modelos
│
├── scripts/
│   ├── README.md           ← documentación del pipeline de scripts
│   ├── reindex_e5.py       ← reindexado con e5-large ← USAR ESTE
│   ├── check_chroma.py     ← diagnóstico rápido BD
│   ├── check_chroma2.py    ← inspección de calidad
│   ├── test_busqueda.py    ← validación post-reindexado
│   ├── rag_query.py        ← CLI standalone RAG
│   ├── demo_embeddings.py  ← demo educativa
│   ├── reindex_limpio.py   ← v1 histórico (MiniLM)
│   └── reindex_v2.py       ← v2 histórico (MiniLM)
│
├── corpus_astro/           ← subtítulos descargados (NO en git)
│   └── NombreCanal/
│       ├── fecha_id_titulo.es.vtt
│       └── fecha_id_titulo.info.json
│
├── astro_knowledge.db      ← SQLite metadatos (NO en git)
└── chroma_db/              ← base vectorial e5-large 1024d (NO en git)
```

---

## 🤔 FAQ

**¿Por qué el retrieval devolvía resultados incorrectos si no había error?**

Los bugs de embeddings son silenciosos: el sistema devuelve resultados, pero son los incorrectos. Sin error en consola, sin excepción. La única forma de detectarlos es verificar las dimensiones explícitamente y hacer un test de retrieval con ground truth conocido (un vídeo cuyo título conoces y puedes verificar). Por eso el self-check es parte permanente del código en v4.

**¿Por qué los procesos se acumulaban en puertos 7861, 7862, 7863...?**

Gradio, al encontrar el puerto 7860 ocupado por un proceso anterior no terminado correctamente, escala al siguiente disponible. Con `PORT = 7860` y `server_name="127.0.0.1"` en `app.launch()`, el proceso falla si el puerto está ocupado en lugar de escalar silenciosamente. Solución: matar los procesos Python antes de relanzar.

**¿Cuánto espacio ocupa todo?**

| Elemento | Tamaño aproximado |
|---|---|
| Modelo e5-large | ~2.1 GB |
| 277 VTTs (corpus Isabel Pareja) | ~40 MB |
| ChromaDB (10.363 chunks, 1024 dims) | ~400 MB |
| SQLite metadatos | ~5 MB |

**¿Funciona en macOS/Linux?**

Sí. Cambiar las rutas absolutas de Windows en la cabecera de `astro_corpus_ui.py` a rutas Unix.

**¿Puedo usar otro LLM además de Qwen?**

Sí. Cambia `LM_MODEL` a cualquier modelo disponible en LM Studio. Para texto generativo (no código) se recomienda un modelo conversacional como `Mistral-7B-Instruct` o `Llama-3-8B-Instruct`.

---

## ⚖️ Consideraciones legales y éticas

- El proyecto descarga subtítulos generados automáticamente por YouTube
- Uso **estrictamente personal** — no redistribuir el corpus
- Respetar los términos de servicio de YouTube
- Si un creador solicita eliminación de su contenido de tu BD local, hazlo

---

## 🙏 Créditos

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — descarga de subtítulos
- [ChromaDB](https://github.com/chroma-core/chroma) — base vectorial local
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) — embeddings
- [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large) — modelo de embeddings
- [Gradio](https://github.com/gradio-app/gradio) — interfaz web
- [LM Studio](https://lmstudio.ai) — servidor LLM local

---

## 📄 Licencia

MIT License — úsalo, modifícalo, compártelo.

---

*Proyecto desarrollado para investigación astrológica personal.*
