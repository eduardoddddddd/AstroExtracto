# 🪐 AstroExtracto

> Base de conocimiento astrológico personal construida desde canales de YouTube en castellano, con búsqueda semántica RAG y consultas en lenguaje natural vía LLM.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Gradio](https://img.shields.io/badge/Interface-Gradio-orange)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-purple)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-En%20desarrollo-yellow)

---

## 📖 Descripción

AstroExtracto es una herramienta **100% local** que permite construir una base de conocimiento astrológico personal a partir de las transcripciones de canales de YouTube seleccionados por el usuario.

El objetivo no es reemplazar al astrólogo sino **potenciar la investigación personal**: dado un corpus de decenas o cientos de horas de contenido en audio/vídeo, permite consultar ese conocimiento acumulado por significado semántico, no por palabras clave exactas.

### ¿Qué problema resuelve?

Un astrólogo que sigue 10 canales de YouTube en castellano acumula cientos de horas de contenido. Cuando quiere saber *"¿qué dicen sobre Saturno en Escorpio en casa 8?"*, no puede buscar ese fragmento concreto entre 500 vídeos. AstroExtracto lo hace posible en segundos.

---

## ✨ Características

| Característica | Detalle |
|---|---|
| 📥 Descarga masiva | `yt-dlp` descarga subtítulos sin bajar el vídeo |
| 📄 Soporte VTT y SRT | Funciona sin `ffmpeg` instalado |
| 🗄️ Base vectorial local | ChromaDB, sin datos en la nube |
| 🔍 Búsqueda semántica | Embeddings multilingües, entiende castellano |
| 🖥️ Interfaz visual | Gradio, se abre en el navegador con un comando |
| 🤖 RAG sobre LLM | Integración con Claude API para respuestas elaboradas |
| 📊 SQLite metadatos | Trazabilidad completa: canal, vídeo, URL, fecha |
| ⚡ 100% local | Sin suscripciones, sin API keys obligatorias para lo básico |


---

## 🏗️ Arquitectura

```
YouTube Channels (URLs seleccionadas por el usuario)
          │
          ▼
    ┌─────────────┐
    │   yt-dlp    │  ← descarga subtítulos (.vtt/.srt) + metadatos (.json)
    └──────┬──────┘       sin descargar el vídeo (~10-30 min por 1000 vídeos)
           │
           ▼
    ┌─────────────┐
    │  Limpieza   │  ← elimina timestamps, tags HTML, ruido VTT/SRT
    │  de texto   │     limpiar_vtt() / limpiar_srt()
    └──────┬──────┘
           │
     ┌─────┴──────┐
     │            │
     ▼            ▼
┌─────────┐  ┌────────────────────────────────┐
│ SQLite  │  │         ChromaDB               │
│         │  │   (base vectorial local)        │
│ id      │  │                                 │
│ canal   │  │  documento (chunk 500 chars)    │
│ titulo  │  │  + embedding (384 dims)         │
│ fecha   │  │  + metadata {canal, url, chunk} │
│ url     │  │                                 │
└─────────┘  └──────────────┬─────────────────┘
                             │
               ┌─────────────▼──────────────┐
               │     Consulta del usuario    │
               │     (lenguaje natural)      │
               └─────────────┬──────────────┘
                             │
               ┌─────────────▼──────────────┐
               │  sentence-transformers      │
               │  paraphrase-multilingual    │  ← embedding pregunta
               │  MiniLM-L12-v2             │
               └─────────────┬──────────────┘
                             │
               ┌─────────────▼──────────────┐
               │  ChromaDB query             │
               │  Top-K chunks relevantes    │  ← recuperación semántica
               └─────────────┬──────────────┘
                             │
               ┌─────────────▼──────────────┐
               │  [OPCIONAL] Claude API      │
               │  RAG: contexto + pregunta   │  ← respuesta elaborada
               │  → respuesta con fuentes    │     con citas de canal/vídeo
               └────────────────────────────┘
```

### Stack tecnológico

| Capa | Tecnología | Motivo |
|---|---|---|
| Descarga | `yt-dlp` | Estándar, activamente mantenido, sin API key |
| Interfaz | `Gradio` | Web local sin configuración, streaming de logs |
| Embeddings | `sentence-transformers` | Modelo multilingüe, corre en CPU/GPU local |
| Vector DB | `ChromaDB` | Persistente, local, sin servidor externo |
| Metadatos | `SQLite` | Sin dependencias, portable, suficiente para este volumen |
| LLM (RAG) | `Claude API` (Anthropic) | Opcional para la fase de generación |


---

## 🚀 Instalación

### Requisitos

- Python 3.9 o superior
- Windows / Linux / macOS
- ~2 GB espacio en disco para el modelo de embeddings (se descarga automáticamente la primera vez)
- Conexión a internet (solo para descargar subtítulos y el modelo, una sola vez)

### Instalación rápida

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/AstroExtracto.git
cd AstroExtracto

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Arrancar la interfaz
python astro_corpus_ui.py
```

La interfaz se abre automáticamente en `http://localhost:7860`

### Dependencias (`requirements.txt`)

```
yt-dlp>=2024.1.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
gradio>=4.0.0
```

### Instalación opcional (mejora calidad de subtítulos)

```bash
# ffmpeg — convierte VTT a SRT con mejor limpieza
# Windows (con winget):
winget install ffmpeg

# Linux:
sudo apt install ffmpeg

# macOS:
brew install ffmpeg
```

> ⚠️ Sin ffmpeg el programa funciona igualmente, usando los archivos VTT directamente.

---

## 📋 Uso

### 1. Ingestar canales

1. Abre la pestaña **📡 Ingestar canales**
2. Introduce una o varias URLs de canales YouTube (una por línea)
3. Pulsa **▶ Descargar e indexar**
4. Observa el log en tiempo real

Formatos de URL aceptados:
```
https://www.youtube.com/@NombreCanal/videos     ← canal completo
https://www.youtube.com/c/NombreCanal/videos    ← formato alternativo
https://www.youtube.com/playlist?list=PLxxxx    ← playlist específica
https://www.youtube.com/watch?v=VIDEO_ID        ← vídeo individual
```

Si ya tienes los subtítulos descargados previamente, usa el botón **🔄 Reindexar lo ya descargado** para no volver a descargar.

### 2. Consultar el corpus

1. Abre la pestaña **🔍 Consultar**
2. Escribe tu consulta en lenguaje natural
3. Ajusta el número de resultados con el slider
4. Pulsa **Buscar**

Ejemplos de consultas efectivas:
```
Saturno Neptuno conjunción significado mundano
Luna en casa 12 emociones ocultas
Nodo norte Piscis misión de vida
rectificación carta natal técnicas
tránsitos Plutón transformación crisis
astrocartografía líneas AC DC
```

> 💡 **Tip**: La búsqueda es semántica, no literal. No necesitas usar las palabras exactas que usó el astrólogo — el sistema entiende el concepto.

### 3. Estado de la base de datos

La pestaña **📊 Estado** muestra:
- Número total de vídeos indexados
- Número de fragmentos (chunks) en la base vectorial
- Desglose por canal


---

## 🔬 Cómo funciona por dentro

### Fase 1 — Descarga de subtítulos

`yt-dlp` recorre el canal completo y descarga únicamente los archivos de texto:

```bash
yt-dlp \
  --skip-download \          # no descarga el vídeo
  --write-auto-subs \        # subtítulos automáticos de YouTube
  --sub-lang es \            # solo español
  --write-info-json \        # metadatos del vídeo
  --output "%(channel)s/%(upload_date)s_%(id)s_%(title)s.%(ext)s" \
  URL_DEL_CANAL
```

Resultado por vídeo:
```
corpus_astro/
  NombreCanal/
    20240315_ABC123_Titulo del video.es.vtt    ← transcripción
    20240315_ABC123_Titulo del video.info.json ← metadatos
```

### Fase 2 — Limpieza del texto

Los archivos VTT tienen mucho ruido que hay que eliminar:

```
WEBVTT
Kind: captions
Language: es

00:00:01.240 --> 00:00:04.880 align:start position:0%
hola a todos bienvenidos
<00:00:02.120><c> bienvenidos</c><00:00:03.600><c> a</c>

→ "hola a todos bienvenidos a este vídeo sobre astrología..."
```

### Fase 3 — Chunking y embeddings

El texto limpio se divide en fragmentos solapados de 500 caracteres (con 50 de solapamiento) para preservar el contexto entre fragmentos:

```python
chunk_1: "...cuando saturno entra en capricornio las estructuras sociales..."
chunk_2: "...las estructuras sociales se someten a una revisión profunda..."
chunk_3: "...revisión profunda que puede durar hasta tres años dependiendo..."
```

Cada chunk se convierte en un vector de 384 dimensiones usando el modelo `paraphrase-multilingual-MiniLM-L12-v2`.

### Fase 4 — Búsqueda semántica

Al hacer una consulta:
1. La pregunta se convierte al mismo espacio vectorial
2. ChromaDB calcula la distancia coseno con todos los chunks
3. Devuelve los K más cercanos semánticamente

Esto permite que *"restricción emocional Saturno-Luna"* encuentre fragmentos que hablan de *"el bloqueo afectivo de Saturno en aspecto a la Luna"* aunque no compartan ninguna palabra.

### Fase 5 — RAG con LLM (próximamente)

Los chunks recuperados se envían como contexto a Claude:

```
SISTEMA: Eres un asistente de astrología. Responde SOLO basándote
en los fragmentos proporcionados. Cita el canal y vídeo de origen.

CONTEXTO:
[Canal: Isabel Pareja | Vídeo: "Saturno en Casa 8"]
"...cuando saturno transita la casa ocho nos encontramos con..."

[Canal: OtroAstrólogo | Vídeo: "Tránsitos de Saturno"]
"...el tránsito de saturno por la octava casa suele coincidir..."

PREGUNTA: ¿Qué significa Saturno en casa 8?
```

---

## 📁 Estructura del proyecto

```
AstroExtracto/
├── astro_corpus_ui.py      ← aplicación principal (Gradio)
├── requirements.txt        ← dependencias
├── README.md               ← este archivo
├── .gitignore              ← excluye corpus y bases de datos
│
├── corpus_astro/           ← subtítulos descargados (NO en git)
│   └── NombreCanal/
│       ├── fecha_id_titulo.es.vtt
│       └── fecha_id_titulo.info.json
│
├── astro_knowledge.db      ← SQLite metadatos (NO en git)
└── chroma_db/              ← base vectorial (NO en git)
    └── chroma.sqlite3
```

---

## ⚙️ Configuración

Las rutas y parámetros principales están en la cabecera de `astro_corpus_ui.py`:

```python
DIRECTORIO   = "./corpus_astro"     # dónde se guardan los subtítulos
DB_PATH      = "./astro_knowledge.db"  # SQLite de metadatos
CHROMA_PATH  = "./chroma_db"        # base vectorial
MODELO_NAME  = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE   = 500    # caracteres por fragmento
CHUNK_OVERLAP= 50     # solapamiento entre fragmentos
```

Para mejorar la calidad de búsqueda puedes experimentar con:
- `CHUNK_SIZE = 800` — fragmentos más grandes, más contexto por resultado
- `CHUNK_OVERLAP = 100` — más solapamiento, menos pérdida en fronteras
- Modelo alternativo: `paraphrase-multilingual-mpnet-base-v2` (más lento pero mejor)


---

## 🗺️ Roadmap

### ✅ v1.0 — MVP (completado)
- [x] Descarga masiva de subtítulos con yt-dlp
- [x] Soporte VTT nativo (sin ffmpeg)
- [x] Indexación en ChromaDB con embeddings multilingües
- [x] SQLite para metadatos
- [x] Interfaz Gradio con logs en tiempo real
- [x] Búsqueda semántica básica

### 🔄 v1.5 — Calidad de búsqueda (en desarrollo)
- [ ] RAG completo con Claude API — respuestas elaboradas con citas
- [ ] Reranking de resultados por relevancia
- [ ] Filtros por canal, fecha, rango temporal
- [ ] Deduplicación de fragmentos muy similares
- [ ] Diccionario de correcciones para terminología astrológica

### 🔮 v2.0 — Funcionalidades avanzadas
- [ ] Soporte Whisper para vídeos sin subtítulos automáticos
- [ ] Resumen automático por vídeo al indexar
- [ ] Mapa conceptual de temas (clustering semántico)
- [ ] Comparativa de perspectivas entre astrólogos sobre un mismo tema
- [ ] Exportación de fragmentos a Markdown/PDF
- [ ] Soporte para podcasts (MP3/RSS)

### 💡 Ideas futuras
- [ ] Integración con software de cartas natales (Astro.com API)
- [ ] Contextualización automática: dado un tránsito, buscar qué dice el corpus
- [ ] Timeline: qué dijo cada canal sobre un evento astrológico específico

---

## 🤔 Preguntas frecuentes

**¿Por qué las búsquedas a veces no son muy precisas?**

La calidad depende de varios factores:
1. **Calidad de los subtítulos automáticos** — YouTube genera subtítulos sin puntuación y con errores fonéticos en términos técnicos astrológicos
2. **Tamaño del corpus** — con más vídeos indexados, hay más posibilidades de encontrar el fragmento relevante
3. **Formulación de la consulta** — probar variaciones de la misma pregunta mejora los resultados
4. **Modelo de embeddings** — el modelo actual es eficiente pero no especializado en astrología

La fase RAG (v1.5) mejorará notablemente la experiencia porque el LLM sintetizará varios fragmentos en una respuesta coherente.

**¿Los datos salen de mi ordenador?**

Solo en dos casos opcionales:
- Al descargar subtítulos de YouTube (tráfico hacia los servidores de Google)
- Al usar la integración con Claude API para RAG (los fragmentos recuperados se envían a Anthropic)

Todo lo demás — almacenamiento, indexación, búsqueda — es 100% local.

**¿Cuánto espacio ocupa?**

| Elemento | Tamaño aproximado |
|---|---|
| Modelo de embeddings | ~500 MB (se descarga una vez) |
| 300 vídeos (subtítulos) | ~50-100 MB |
| ChromaDB (300 vídeos) | ~200-400 MB |
| SQLite (300 vídeos) | ~5 MB |

**¿Funciona en macOS/Linux?**

Sí. Las rutas del código están configuradas para Windows por defecto. En macOS/Linux cambia `DIRECTORIO`, `DB_PATH` y `CHROMA_PATH` a rutas Unix (`/home/usuario/...`).

**¿Puedo añadir canales en inglés?**

Sí, el modelo `paraphrase-multilingual-MiniLM-L12-v2` soporta múltiples idiomas. Cambiar `--sub-lang es` a `--sub-lang en` en el comando yt-dlp.

---

## ⚖️ Consideraciones legales y éticas

- Este proyecto descarga subtítulos generados automáticamente por YouTube
- El uso es **estrictamente personal** — no redistribuyas el corpus ni lo uses comercialmente
- Los subtítulos automáticos son generados por los propios sistemas de Google, no son obra directa del creador de contenido en el sentido técnico, pero el contenido de los vídeos sí lo es
- Respeta los términos de servicio de YouTube
- Si un creador solicita que elimines su contenido de tu base de datos local, hazlo

---

## 🙏 Créditos y agradecimientos

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — el mejor descargador de vídeo/subtítulos
- [ChromaDB](https://github.com/chroma-core/chroma) — base de datos vectorial local
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) — embeddings multilingües
- [Gradio](https://github.com/gradio-app/gradio) — interfaces web para ML sin configuración
- [Anthropic Claude](https://anthropic.com) — LLM para la fase RAG

---

## 📄 Licencia

MIT License — úsalo, modifícalo, compártelo. Ver [LICENSE](LICENSE).

---

*Proyecto desarrollado para investigación astrológica personal.*
*"La astrología es el lenguaje del tiempo." — Anónimo*
