# scripts/

Scripts de utilidad desarrollados durante la construcción de AstroExtracto.
No forman parte del flujo principal (`astro_corpus_ui.py`) pero documentan
el proceso de diagnóstico, limpieza e indexado del corpus.

## Orden cronológico de uso

| Script | Propósito |
|--------|-----------|
| `check_chroma.py` | Diagnóstico inicial: busca la BD y lista colecciones con conteo |
| `check_chroma2.py` | Inspección de calidad: búsquedas de prueba para detectar texto triplicado |
| `demo_embeddings.py` | Demostración educativa de similitud coseno con MiniLM-L12-v2 |
| `reindex_limpio.py` | **Script principal de indexado**: limpieza VTT en dos capas + reindexado completo |
| `test_busqueda.py` | Validación post-indexado: búsquedas con embeddings reales para verificar calidad |

## Problema resuelto

Los VTTs de YouTube de Isabel Pareja tenían ruido en dos capas:
1. Solapamiento de subtítulos → líneas triplicadas
2. Etiquetas de sincronización → `<00:43:00.480><c>texto</c>`

Resultado antes de limpiar: **46.289 chunks** con texto incoherente.  
Resultado tras `reindex_limpio.py`: **5.252 chunks** con castellano limpio.

## Uso

```bash
# Verificar que la BD existe y tiene datos
python scripts/check_chroma.py

# Reindexar desde cero (tarda ~3 min en 277 VTTs)
python scripts/reindex_limpio.py

# Validar calidad de búsquedas
python scripts/test_busqueda.py
```
