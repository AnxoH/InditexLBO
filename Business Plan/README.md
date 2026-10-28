# Business plan de Inditex (2026-2030)

Business plan estocástico para el LBO: calibración con el histórico 2005-2025 y la guía de Inditex para 2026, 20.000 caminos de Monte Carlo, un motor LBO que replica la hoja `LBO_Rollover50` del Excel del grupo y un plan de creación de valor con 8 palancas.

**Por dónde empezar**

0. [Guia_Business_Plan_desde_cero.pdf](Guia_Business_Plan_desde_cero.pdf): todo explicado desde cero (conceptos, cada hipótesis y su justificación, el Excel hoja por hoja, el dashboard y preguntas para la presentación).
1. [Business_Plan_Inditex.ipynb](Business_Plan_Inditex.ipynb): el business plan standalone, explicado paso a paso.
2. `output/Dashboard_palancas.html` (doble clic): dashboard con las 8 palancas, barómetros, TIR y riesgo en 20.000 escenarios. La pestaña «Gráficas del LBO» redibuja al mover cada palanca la TIR de los cuatro casos, ventas, margen, deuda por tramos, DSCR y el puente de valor del equity. Sus valores se pasan a la hoja Palancas del Excel pegando la columna que copia el botón «Copiar columna» en la celda D19, o con `.venv/bin/python "Business Plan/pasar_al_excel.py"` (con el Excel cerrado).
3. `../Excels/Inditex_LBO_Rollover50_BusinessPlan.xlsx`, hoja **Palancas**: el mismo panel dentro del Excel. Cambia las celdas amarillas; el barómetro indica si cada hipótesis es conservadora, normal, optimista o agresiva, y el LBO se recalcula al instante.
4. [Plan_de_creacion_de_valor.ipynb](Plan_de_creacion_de_valor.ipynb): lee los valores del panel y calcula el riesgo, el reparto de la TIR por palanca y «qué pasa si hago todas».

| Carpeta / archivo | Contenido |
|---|---|
| `data/` | Histórico 2005-2025 (fuente por fila) y detalle operativo 2021-2025 de las cuentas anuales |
| `bp/calibration.py` | Estimación de los procesos: divisa, crecimiento, margen bruto AR(1), modelo de corrección de error de los gastos, crisis, guía 2026 |
| `bp/model.py` | Árbol de drivers y simulación de Monte Carlo |
| `bp/lbo.py` | Motor LBO vectorizado (cascada de deuda, cash sweep, PIK, límite fiscal del 30 %, PropCo, recap, TIR XIRR) |
| `bp/analysis.py` | Casos por percentiles, frontera de apalancamiento, capacidad de deuda senior, valores de Shapley |
| `bp/levers.py` | Las 8 palancas: aritmética, bandas del barómetro y datos que las anclan |
| `bp/plan.py` | Plan bajo incertidumbre: escenarios por banda, reparto de Shapley por palanca, rentabilidad por euro invertido |
| `bp/dashboard.py` | Hojas Palancas y Palancas_calc del Excel integrado (mismas fórmulas que `levers.py`) |
| `bp/web.py`, `dashboard/` | Dashboard web: plantilla HTML y motor en JavaScript (`motor.js`, traducción de `lbo.py` y `levers.py`) |
| `pasar_al_excel.py` | Escribe en la hoja Palancas los valores copiados del dashboard (solo las celdas D19:D62) |
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
.venv/bin/python "Business Plan/tests/test_business_plan.py"
.venv/bin/python "Business Plan/tests/test_levers.py"
.venv/bin/python "Business Plan/tests/test_dashboard.py"
cd "Business Plan" && ../.venv/bin/python -m bp.web   # regenera el dashboard
```

El Excel integrado solo se regenera si `Excels/Inditex_LBO_Rollover50.xlsx` (rama `Javi`) está en la carpeta. Las pruebas de paridad Excel ↔ Python y dashboard ↔ Python necesitan `pycel` y `mini-racer` (incluidos en `requirements.txt`); sin ellos, se saltan.
