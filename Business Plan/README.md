# Business plan de Inditex

Business plan estocástico para el LBO: calibración con el histórico 2005-2025 y la guía de Inditex para 2026, 20.000 caminos de Monte Carlo, un plan de creación de valor con 8 palancas y dos motores LBO:

- `bp/definitiva.py` replica el **modelo definitivo del grupo** ([`../Inditex_LBO_Version_Definitiva.xlsx`](../Inditex_LBO_Version_Definitiva.xlsx): rollover del 25 %, 7 años, cascada GP/LP) y lee del propio Excel sus hipótesis y sus cuatro casos. Es el que usa el dashboard interactivo.
- `bp/lbo.py` replica la versión preliminar de calibración inicial (`LBO_Rollover50`). La usan los notebooks originales y la guía en PDF.

**Por dónde empezar**

0. [Guia_Business_Plan_desde_cero.pdf](Guia_Business_Plan_desde_cero.pdf): todo explicado desde cero (conceptos, cada hipótesis y su justificación, el Excel hoja por hoja, el dashboard, preguntas para la presentación y, en la Parte 7, el modelo ecuación a ecuación con qué pasa si mueves cada parámetro).
1. [Business_Plan_Inditex.ipynb](Business_Plan_Inditex.ipynb): el business plan standalone, explicado paso a paso.
2. `output/Dashboard_palancas.html` (doble clic): dashboard sobre el **modelo definitivo del grupo** ([`../Inditex_LBO_Version_Definitiva.xlsx`](../Inditex_LBO_Version_Definitiva.xlsx)). Sin palancas da exactamente lo que el Excel (TIR bruta del fondo, TIR neta de LPs y GP, DSCR bancario, covenants), en cualquiera de los cuatro casos y años de salida. El panel «Estructura de la operación» deja cambiar las mismas celdas que el Excel (prima, rollover, cada tramo de deuda, nota de Sandra Ortega, Euribor, sweep, reparto GP/LP, hurdle, carry y múltiplo de salida) y dice qué celda tocar para comprobarlo; encima se suman las 8 palancas con sus barómetros. Pestañas: Resumen, Gráficas del LBO (TIR por caso y por año de salida, ventas, margen, deuda por tramos, DSCR, puente del equity, reparto LPs/GP) y Riesgo (20.000 escenarios a siete años centrados en el caso Base del Excel).
3. [Plan_de_creacion_de_valor.ipynb](Plan_de_creacion_de_valor.ipynb): lee los valores del panel y calcula el riesgo, el reparto de la TIR por palanca y «qué pasa si hago todas».

| Carpeta / archivo | Contenido |
|---|---|
| `data/` | Histórico 2005-2025 (fuente por fila) y detalle operativo 2021-2025 de las cuentas anuales |
| `bp/calibration.py` | Estimación de los procesos: divisa, crecimiento, margen bruto AR(1), modelo de corrección de error de los gastos, crisis, guía 2026 |
| `bp/model.py` | Árbol de drivers y simulación de Monte Carlo |
| `bp/definitiva.py` | Réplica del Excel definitivo ([`../Inditex_LBO_Version_Definitiva.xlsx`](../Inditex_LBO_Version_Definitiva.xlsx)): lectura de hipótesis y casos, cascada de deuda, impuesto con límite del 30 % y arrastre, covenants, salida en cualquier año, cascada GP/LP, palancas y caminos simulados |
| `bp/lbo.py` | Motor LBO de la versión preliminar `LBO_Rollover50` (cascada de deuda, cash sweep, PIK, límite fiscal del 30 %, PropCo, recap, TIR XIRR) |
| `bp/analysis.py` | Casos por percentiles, frontera de apalancamiento, capacidad de deuda senior, valores de Shapley |
| `bp/levers.py` | Las 8 palancas: aritmética, bandas del barómetro y datos que las anclan |
| `bp/plan.py` | Plan bajo incertidumbre: escenarios por banda, reparto de Shapley por palanca, rentabilidad por euro invertido |
| `bp/dashboard.py` | Hojas Palancas y Palancas_calc del Excel integrado (mismas fórmulas que `levers.py`) |
| `bp/web.py`, `dashboard/` | Dashboard web: plantilla HTML y motor en JavaScript (`motor.js`, traducción de `definitiva.py` y `levers.py`) |
| `pasar_al_excel.py` | Escribe una columna de valores de las palancas en la hoja Palancas del Excel preliminar (celdas D19:D62) |
| `figures/` | Gráficos para la presentación |
| `output/Business_Plan_Inditex.xlsx` | Casos en formato de las filas 10-17 del Excel, PyG y caja, plan de creación de valor, percentiles, apalancamiento y calibración |

El PDF, el dashboard y el Excel se abren sin instalar nada. Para ejecutar los notebooks y los tests hay que crear antes el entorno, desde la carpeta del repositorio:

```bash
python3 -m venv .venv
.venv/bin/pip install -r "Business Plan/requirements.txt"
```

Regenerar todo y pasar los tests (el segundo notebook debe ir después del primero):

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace "Business Plan/Business_Plan_Inditex.ipynb"
.venv/bin/jupyter nbconvert --to notebook --execute --inplace "Business Plan/Plan_de_creacion_de_valor.ipynb"
.venv/bin/python "Business Plan/tests/test_definitiva.py"
.venv/bin/python "Business Plan/tests/test_business_plan.py"
.venv/bin/python "Business Plan/tests/test_levers.py"
.venv/bin/python "Business Plan/tests/test_dashboard.py"
cd "Business Plan" && ../.venv/bin/python -m bp.web   # regenera el dashboard leyendo el Excel definitivo
```

Si el grupo cambia el Excel definitivo ([`../Inditex_LBO_Version_Definitiva.xlsx`](../Inditex_LBO_Version_Definitiva.xlsx)), basta con regenerar el dashboard y pasar `test_definitiva.py`. Las pruebas de paridad Excel ↔ Python (con pycel recalcula el Excel en los cuatro casos) y dashboard ↔ Python necesitan `pycel` y `mini-racer` (incluidos en `requirements.txt`); sin ellos, se saltan.
