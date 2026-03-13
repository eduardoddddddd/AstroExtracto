"""
demo_embeddings.py — Demostración de similitud coseno con embeddings
=====================================================================
Script educativo/de diagnóstico que muestra cómo funciona internamente
el motor de búsqueda semántica: genera vectores de 384 dimensiones para
varias frases y calcula la similitud coseno entre ellas.

Sirve para entender por qué la búsqueda semántica encuentra "bloqueo
afectivo herida emocional" cuando se busca "Saturno en casa 8" aunque
no compartan palabras literales — porque sus vectores están cerca en el
espacio de 384 dimensiones.

También sirve como smoke test: si el modelo no carga o la similitud
entre frases semánticamente idénticas es baja, algo va mal.

Modelo: paraphrase-multilingual-MiniLM-L12-v2 (117M parámetros, 384d)
Métrica: similitud coseno (1.0 = idéntico, 0.0 = sin relación)

USO: python demo_embeddings.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from sentence_transformers import SentenceTransformer
import numpy as np
from numpy.linalg import norm

modelo = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

frases = [
    'Saturno en casa 8 restriccion emocional bloqueo',
    'el transito de saturno por la octava casa genera profundos cambios',
    'bloqueo afectivo herida emocional de Saturno',
    'receta de paella valenciana con pollo',
]

vectores = modelo.encode(frases)

print(f'Cada frase -> vector de {vectores.shape[1]} dimensiones\n')

for frase, vec in zip(frases, vectores):
    print(f'FRASE : {frase}')
    print(f'VECTOR: [{vec[0]:.3f}, {vec[1]:.3f}, {vec[2]:.3f}, {vec[3]:.3f}, {vec[4]:.3f} ... ({len(vec)} dims total)]')
    print()

def coseno(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))

print('=== SIMILITUD COSENO (1.0=identicos  0.0=sin relacion) ===\n')
for i in range(len(frases)):
    for j in range(i + 1, len(frases)):
        sim = coseno(vectores[i], vectores[j])
        etiqueta = '<<< MUY SIMILAR' if sim > 0.7 else ('similar' if sim > 0.5 else '(poco relacionado)')
        print(f'{sim:.3f}  {etiqueta}')
        print(f'       A: {frases[i]}')
        print(f'       B: {frases[j]}')
        print()
