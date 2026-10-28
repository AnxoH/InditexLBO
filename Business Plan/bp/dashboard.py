"""Panel de control del plan de creación de valor dentro del Excel integrado.

Hoja «Palancas»: inputs con barómetro de bandas y resultados en vivo.
Hoja «Palancas_calc»: la misma aritmética que bp/levers.py, en fórmulas, que alimenta
las filas 10-17 de LBO_Rollover50 (más la PropCo en la fila 195 y el recap en la 88).
"""

from __future__ import annotations

import numpy as np
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

from . import levers as L
from .lbo import YEARS

LBO = "LBO_Rollover50"
YC = ["D", "E", "F", "G", "H"]  # años 2026-2030 en Palancas_calc (C = 2025)
BP_COLS = ["N", "O", "P", "Q", "R"]  # mismas años en Business_Plan y LBO_Rollover50
GAUGE = 12
BAND_FILL = {"Conservador": "FFB7D3F6", "Normal": "FFBFE6D6", "Optimista": "FFFBE3A6", "Agresivo": "FFF4C1C0"}
INPUT_FILL = PatternFill("solid", fgColor="FFFFF2CC")
HEAD_FILL = PatternFill("solid", fgColor="FFF4F7FE")
BLUE = Font(color="FF0000FF", bold=True)
BOLD = Font(bold=True)
THIN = Side(style="thin", color="FFE1E0D9")


def _num(v: float) -> str:
    return repr(float(v))


def build(wb, o: dict, block_rows: dict, control_rows: dict) -> None:
    calc = wb.create_sheet("Palancas_calc", index=wb.sheetnames.index("Business_Plan") + 1)
    ui = wb.create_sheet("Palancas", index=wb.sheetnames.index(LBO))
    inputs = _build_ui(ui, o, control_rows)
    finals = _build_calc(calc, inputs, block_rows)
    _wire_lbo(wb[LBO], finals, inputs)
    _results_panel(ui, inputs, control_rows, finals)


def _build_ui(ws, o: dict, control_rows: dict) -> dict:
    ws["B1"] = "Plan de creación de valor: panel de control"
    ws["B1"].font = Font(bold=True, size=16)
    ws["B2"] = ("Cambia las celdas amarillas. El barómetro muestra en qué banda cae cada hipótesis "
                "(azul conservador · verde normal · amarillo optimista · rojo agresivo). "
                "Todo el modelo LBO se recalcula al instante.")
    ws["B2"].font = Font(italic=True, color="FF52514E")
    ws["B4"] = "Activar plan de creación de valor (1 = sí, 0 = no)"
    ws["D4"] = 1
    ws["B5"] = "Caso operativo (se elige en LBO_Rollover50!F9: 1 Base, 2 Bull, 3 Bear, 4 Bank)"
    ws["D5"] = f"={LBO}!H9"
    for c in ("D4",):
        ws[c].fill, ws[c].font = INPUT_FILL, BLUE
    switch = DataValidation(type="whole", operator="between", formula1="0", formula2="1", allow_blank=False)
    ws.add_data_validation(switch)
    switch.add("D4")

    row = 18
    for col, text in zip("BCDE", ["Palanca / parámetro", "Unidad", "Valor", "Banda"]):
        ws[f"{col}{row}"] = text
    ws.cell(row=row, column=6, value="Barómetro (izquierda = valor bajo · derecha = valor alto)")
    ws.cell(row=row, column=6 + GAUGE, value="Rangos por banda")
    ws.cell(row=row, column=7 + GAUGE, value="Dato que lo ancla")
    for c in range(2, 8 + GAUGE):
        ws.cell(row=row, column=c).font = BOLD
        ws.cell(row=row, column=c).fill = HEAD_FILL
    row += 1

    inputs = {"master": "Palancas!$D$4", "on": {}, "val": {}}
    for lv in L.LEVERS:
        ws.cell(row=row, column=2, value=lv.name).font = Font(bold=True, size=12)
        ws.cell(row=row, column=3, value="Activa (1/0)")
        c = ws.cell(row=row, column=4, value=1)
        c.fill, c.font = INPUT_FILL, BLUE
        switch.add(c.coordinate)
        ws.cell(row=row, column=6 + GAUGE, value=lv.what).font = Font(italic=True, color="FF52514E")
        inputs["on"][lv.key] = f"Palancas!$D${row}"
        row += 1
        for p in lv.params:
            ws.cell(row=row, column=2, value=f"   {p.label}")
            ws.cell(row=row, column=3, value=p.unit)
            vc = ws.cell(row=row, column=4, value=p.default)
            vc.fill, vc.font, vc.number_format = INPUT_FILL, BLUE, p.fmt
            inputs["val"][(lv.key, p.key)] = f"Palancas!$D${row}"
            if p.edges is None:
                dv = DataValidation(type="list", formula1='"2027,2028,2029"', allow_blank=False)
                ws.add_data_validation(dv)
                dv.add(vc.coordinate)
                ws.cell(row=row, column=6 + GAUGE, value="2027, 2028 o 2029 (el recap en el año de salida no cuenta)")
            else:
                b = p.edges
                dv = DataValidation(type="decimal", operator="between", formula1=_num(b[0]), formula2=_num(b[4]),
                                    error=f"Fuera del rango estudiado ({b[0]} a {b[4]})", showErrorMessage=True)
                ws.add_data_validation(dv)
                dv.add(vc.coordinate)
                names = list(L.BANDS) if not p.reverse else list(L.BANDS)[::-1]
                ws.cell(row=row, column=5, value=(
                    f'=IF($D{row}<{_num(b[1])},"{names[0]}",IF($D{row}<{_num(b[2])},"{names[1]}",'
                    f'IF($D{row}<{_num(b[3])},"{names[2]}","{names[3]}")))'))
                step = (b[4] - b[0]) / GAUGE
                for i in range(GAUGE):
                    lo, hi = b[0] + i * step, b[0] + (i + 1) * step
                    cond = f"$D{row}<={_num(hi)}" if i == GAUGE - 1 else f"$D{row}<{_num(hi)}"
                    gc = ws.cell(row=row, column=6 + i, value=f'=IF(AND($D{row}>={_num(lo)},{cond}),"▼","")')
                    gc.fill = PatternFill("solid", fgColor=BAND_FILL[p.band((lo + hi) / 2)])
                    gc.alignment = Alignment(horizontal="center")
                    gc.font = Font(bold=True)
                fmt = (lambda v: f"{v:.0%}" if "%" in p.fmt else f"{v:,.0f}".replace(",", ".") if v >= 1000
                       else f"{v:g}".replace(".", ","))
                ranges = " · ".join(f"{bn} {fmt(p.band_range(bn)[0])}–{fmt(p.band_range(bn)[1])}" for bn in L.BANDS)
                ws.cell(row=row, column=6 + GAUGE, value=ranges)
            ws.cell(row=row, column=7 + GAUGE, value=p.anchor).font = Font(color="FF52514E")
            row += 1
        row += 1

    for name, color in BAND_FILL.items():
        ws.conditional_formatting.add(f"E19:E{row}", CellIsRule(operator="equal", formula=[f'"{name}"'],
                                                                fill=PatternFill("solid", fgColor=color)))
    inputs["contrib_row"] = row + 1
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 58
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 13
    ws.column_dimensions["E"].width = 13
    for i in range(GAUGE):
        ws.column_dimensions[chr(ord("F") + i)].width = 3
    ws.column_dimensions[chr(ord("F") + GAUGE)].width = 70
    ws.column_dimensions[chr(ord("F") + GAUGE + 1)].width = 80
    ws.freeze_panes = "C19"
    return inputs


def _build_calc(ws, inp: dict, block_rows: dict) -> dict:
    v = lambda lever, param: inp["val"][(lever, param)]
    on = lambda lever: f'({inp["master"]}*{inp["on"][lever]})'
    ws["B1"] = "Cálculo de las palancas (no tocar: se alimenta de la hoja Palancas)"
    ws["B1"].font = Font(bold=True, size=14)
    ws["C3"] = 2025
    for c, y in zip(YC, YEARS):
        ws[f"{c}3"] = int(y)
    for c in ["C"] + YC:
        ws[f"{c}3"].font = BOLD
        ws[f"{c}3"].fill = HEAD_FILL

    r = 4
    labels = ["Crecimiento de ventas", "Margen bruto", "Crecimiento de gastos (sin alquileres fijos)",
              "Crecimiento de alquileres fijos", "Capex / ventas", "Existencias / ventas", "Clientes / ventas",
              "Proveedores / ventas"]
    cases = ["Base", "Bull", "Bear", "Bank case"]
    base = {}
    ws[f"B{r}"] = "1. Drivers del caso seleccionado (sin palancas)"
    ws[f"B{r}"].font = BOLD
    r += 1
    for i, lab in enumerate(labels):
        ws[f"B{r}"] = lab
        for c, bpc in zip(YC, BP_COLS):
            refs = ",".join(f"Business_Plan!{bpc}{block_rows[cs] + i}" for cs in cases)
            ws[f"{c}{r}"] = f"=IF({LBO}!$F$18=1,CHOOSE({LBO}!$F$9,{refs}),{LBO}!$H${10 + i})"
            ws[f"{c}{r}"].number_format = "0.0%"
        base[i] = r
        r += 1

    r += 1
    ws[f"B{r}"] = "2. Caso seleccionado en euros (€m)"
    ws[f"B{r}"].font = BOLD
    r += 1
    rows = {}
    for key, lab, start in [("rev", "Ventas", 39864), ("gp", "Margen bruto", None), ("opex", "Gastos (sin alquileres fijos)", 11955),
                            ("lease", "Alquileres fijos", 1834), ("ebitda", "EBITDA pre-IFRS 16", 9433),
                            ("capex", "Capex", None)]:
        ws[f"B{r}"] = lab
        if start is not None:
            ws[f"C{r}"] = start
        rows[key] = r
        r += 1
    prev = lambda c: chr(ord(c) - 1)
    for c in YC:
        ws[f"{c}{rows['rev']}"] = f"={prev(c)}{rows['rev']}*(1+{c}{base[0]})"
        ws[f"{c}{rows['gp']}"] = f"={c}{rows['rev']}*{c}{base[1]}"
        ws[f"{c}{rows['opex']}"] = f"={prev(c)}{rows['opex']}*(1+{c}{base[2]})"
        ws[f"{c}{rows['lease']}"] = f"={prev(c)}{rows['lease']}*(1+{c}{base[3]})"
        ws[f"{c}{rows['ebitda']}"] = f"={c}{rows['gp']}-{c}{rows['opex']}-{c}{rows['lease']}"
        ws[f"{c}{rows['capex']}"] = f"={c}{rows['rev']}*{c}{base[4]}"

    r += 1
    ws[f"B{r}"] = "3. Constantes del modelo de palancas"
    ws[f"B{r}"].font = BOLD
    r += 1
    const = {}
    for key, lab, vals in [("F", "Factor de añadas: ventas (rampa 60/85/100 %, -3 % por añada)", L.F_COHORT),
                           ("G", "Factor de añadas: ventas × margen (rampa de margen 50/80/100 %)", L.G_COHORT),
                           ("H", "Factor de añadas sin pérdida por añada (reformas)", L.H_COHORT),
                           ("t", "Año del plan (1-5)", np.arange(1, 6)),
                           ("wcp", "Calendario de la mejora de circulante", L.WC_PHASE),
                           ("esc", "Indexación del alquiler de la PropCo (2 % anual)", 1.02 ** np.arange(5))]:
        ws[f"B{r}"] = lab
        for c, x in zip(YC, vals):
            ws[f"{c}{r}"] = float(x)
        const[key] = r
        r += 1
    for key, lab, x in [("gm", "Margen EBITDA pre-IFRS 16 del grupo FY2025 (canibalización)", L.GROUP_MARGIN),
                        ("ls", "Alquileres fijos / ventas FY2025", L.LEASE_SHARE),
                        ("bd", "Ventas por m² del grupo FY2025 (€/m²)", L.BASE_DENSITY),
                        ("nbv", "Terrenos y construcciones, valor neto contable (€m)", L.LAND_BUILDINGS_NBV)]:
        ws[f"B{r}"] = lab
        ws[f"C{r}"] = float(x)
        const[key] = f"$C${r}"
        r += 1

    r += 1
    ws[f"B{r}"] = "4. Efecto de cada palanca (€m)"
    ws[f"B{r}"].font = BOLD
    r += 1
    d_rev, d_e, d_cx = [], [], []
    contrib = {}

    def put(label: str, formula_for):
        nonlocal r
        ws[f"B{r}"] = label
        for c in YC:
            ws[f"{c}{r}"] = "=" + formula_for(c)
            ws[f"{c}{r}"].number_format = "#,##0"
        r += 1
        return r - 1

    for key in ("usa", "young", "lefties"):
        name = L.LEVER_BY_KEY[key].name
        scale = f'{on(key)}*{v(key, "m2")}*{v(key, "density")}/1000'
        rr = put(f"{name}: ventas", lambda c: f'{scale}*{c}${const["F"]}*(1-{v(key, "cannib")})')
        re = put(f"{name}: EBITDA", lambda c: (f'{scale}*({v(key, "margin")}*{c}${const["G"]}'
                                               f'-{v(key, "cannib")}*{const["gm"]}*{c}${const["F"]})'))
        rc = put(f"{name}: capex", lambda c: f'{on(key)}*{v(key, "m2")}*{v(key, "capex")}/1000')
        d_rev.append(rr); d_e.append(re); d_cx.append(rc)
        contrib[key] = (rr, re, rc)

    rr = put("Optimización de tiendas: ventas", lambda c: (f'{on("refurb")}*{v("refurb", "m2")}*{const["bd"]}/1000'
                                                          f'*{v("refurb", "uplift")}*{c}${const["H"]}'))
    re = put("Optimización de tiendas: EBITDA", lambda c: f'{c}{rr}*{v("refurb", "margin")}')
    rc = put("Optimización de tiendas: capex", lambda c: f'{on("refurb")}*{v("refurb", "m2")}*{v("refurb", "capex")}/1000')
    d_rev.append(rr); d_e.append(re); d_cx.append(rc)
    contrib["refurb"] = (rr, re, rc)

    re = put("Eficiencia operativa: EBITDA", lambda c: (
        f'{on("efficiency")}*({v("efficiency", "bps")}/10000*{c}{rows["rev"]}'
        f'*MIN(1,{c}${const["t"]}/{v("efficiency", "years")})'
        f'-IF({c}${const["t"]}<=2,0.5*{v("efficiency", "one_off")}*{v("efficiency", "bps")}/10000*$D{rows["rev"]},0))'))
    d_e.append(re)
    contrib["efficiency"] = (None, re, None)

    r_inv = put("Circulante: cambio en existencias / ventas", lambda c: f'-{on("wc")}*{v("wc", "inv")}/100*{c}${const["wcp"]}')
    r_pay = put("Circulante: cambio en proveedores / ventas", lambda c: f'-{on("wc")}*{v("wc", "pay")}/100*{c}${const["wcp"]}')
    for rr_ in (r_inv, r_pay):
        for c in YC:
            ws[f"{c}{rr_}"].number_format = "0.00%"

    ws[f"B{r}"] = "PropCo: ingresos por la venta de inmuebles (fuente al cierre)"
    ws[f"C{r}"] = f'={on("propco")}*{const["nbv"]}*{v("propco", "share")}*{v("propco", "multiple")}'
    ws[f"C{r}"].number_format = "#,##0"
    proceeds = f"Palancas_calc!$C${r}"
    r_proc = r
    r += 1
    r_pl = put("PropCo: nuevo alquiler fijo", lambda c: f'$C${r_proc}*{v("propco", "caprate")}*{c}${const["esc"]}')
    re = put("PropCo: EBITDA", lambda c: f"-{c}{r_pl}")
    d_e.append(re)
    contrib["propco"] = (None, re, None)

    ws[f"B{r}"] = "Recap: activo (1/0)"
    ws[f"C{r}"] = f'={on("recap")}'
    recap_on = f"Palancas_calc!$C${r}"
    r += 2

    ws[f"B{r}"] = "5. Caso con palancas (€m)"
    ws[f"B{r}"].font = BOLD
    r += 1
    sum_of = lambda rows_, c: "+".join(f"{c}{x}" for x in rows_) if rows_ else "0"
    t_rev = put("Ventas incrementales", lambda c: sum_of(d_rev, c))
    t_e = put("EBITDA pre-IFRS 16 incremental", lambda c: sum_of(d_e, c))
    t_cx = put("Capex incremental", lambda c: sum_of(d_cx, c))
    fin = {}
    ws[f"B{r}"] = "Ventas"; ws[f"C{r}"] = 39864; fin["rev"] = r
    for c in YC:
        ws[f"{c}{r}"] = f"={c}{rows['rev']}+{c}{t_rev}"
    r += 1
    fin["gp"] = put("Margen bruto", lambda c: f"{c}{rows['gp']}+{c}{t_rev}*{c}{rows['gp']}/{c}{rows['rev']}")
    ws[f"B{r}"] = "Alquileres fijos"; ws[f"C{r}"] = 1834; fin["lease"] = r
    for c in YC:
        ws[f"{c}{r}"] = f"={c}{rows['lease']}+{c}{t_rev}*{const['ls']}+{c}{r_pl}"
    r += 1
    fin["ebitda"] = put("EBITDA pre-IFRS 16", lambda c: f"{c}{rows['ebitda']}+{c}{t_e}")
    ws[f"B{r}"] = "Gastos (sin alquileres fijos)"; ws[f"C{r}"] = 11955; fin["opex"] = r
    for c in YC:
        ws[f"{c}{r}"] = f"={c}{fin['gp']}-{c}{fin['ebitda']}-{c}{fin['lease']}"
    r += 1
    fin["capex"] = put("Capex", lambda c: f"{c}{rows['capex']}+{c}{t_cx}")
    ws[f"C{fin['ebitda']}"] = 9433
    ws[f"B{r}"] = "Circulante: caja liberada acumulada 2026-30 (€m)"
    ws[f"C{r}"] = f"=-H{fin['rev']}*(H{r_inv}+H{r_pay})"
    ws[f"C{r}"].number_format = "#,##0"
    wc_cash = r
    r += 1
    for k in ("rev", "lease", "opex"):
        for c in ["C"] + YC:
            ws[f"{c}{fin[k]}"].number_format = "#,##0"

    r += 1
    ws[f"B{r}"] = "6. Drivers finales (alimentan LBO_Rollover50!N10:R17)"
    ws[f"B{r}"].font = BOLD
    r += 1
    finals = {}
    formulas = [
        lambda c: f"{c}{fin['rev']}/{prev(c)}{fin['rev']}-1",
        lambda c: f"{c}{fin['gp']}/{c}{fin['rev']}",
        lambda c: f"{c}{fin['opex']}/{prev(c)}{fin['opex']}-1",
        lambda c: f"{c}{fin['lease']}/{prev(c)}{fin['lease']}-1",
        lambda c: f"{c}{fin['capex']}/{c}{fin['rev']}",
        lambda c: f"{c}{base[5]}+{c}{r_inv}",
        lambda c: f"{c}{base[6]}",
        lambda c: f"{c}{base[7]}+{c}{r_pay}",
    ]
    for i, (lab, f) in enumerate(zip(labels, formulas)):
        finals[i] = put(lab, f)
        for c in YC:
            ws[f"{c}{finals[i]}"].number_format = "0.0%"

    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 64
    for c in ["C"] + YC:
        ws.column_dimensions[c].width = 12
    return dict(finals=finals, proceeds=proceeds, recap_on=recap_on, base_rows=rows, fin=fin, contrib=contrib,
                t_cx=t_cx, wc_cash=wc_cash)


def _wire_lbo(lbo, f: dict, inp: dict) -> None:
    for i in range(8):
        for yc, col in zip(YC, BP_COLS):
            lbo[f"{col}{10 + i}"] = f"=Palancas_calc!{yc}{f['finals'][i]}"
    lbo["E195"] = f"=+F173+{f['proceeds']}"
    year, target = inp["val"][("recap", "year")], inp["val"][("recap", "target")]
    for col in BP_COLS:
        pc = chr(ord(col) - 1)
        lbo[f"{col}88"] = (f"=IF(AND({f['recap_on']}=1,{col}$8={year}),"
                           f"MAX(0,{target}*{pc}29-({pc}82+{pc}92+{pc}117-{pc}157)),0)")
        lbo[f"{col}153"] = f"=-{col}88"
        lbo[f"{col}154"] = f"=+{col}149+SUM({col}151:{col}153)+{col}88"


def _results_panel(ws, inp: dict, control_rows: dict, f: dict) -> None:
    ws["B7"] = "Resultado (caso seleccionado)"
    ws["C7"] = "Sin palancas"
    ws["D7"] = "Con palancas"
    ws["E7"] = "Diferencia"
    for c in "BCDE":
        ws[f"{c}7"].font = BOLD
        ws[f"{c}7"].fill = HEAD_FILL
    ctrl = lambda j: f"INDEX(Business_Plan!{chr(ord('N') + j)}{control_rows['first']}:{chr(ord('N') + j)}{control_rows['first'] + 3},{LBO}!$F$9)"
    rows = [
        ("TIR del sponsor", ctrl(0), f"={LBO}!F229", "0.0%"),
        ("MoM del sponsor", ctrl(1), f"={LBO}!F230", '0.00"x"'),
        ("DSCR mínimo 2026-30", ctrl(2), f"={LBO}!Q253", '0.00"x"'),
        ("EBITDA pre-IFRS 16 2030 (€m)", ctrl(3), f"={LBO}!R29", "#,##0"),
        ("Deuda senior neta / EBITDA 2030", ctrl(4), f"={LBO}!R134", '0.00"x"'),
        ("Capex acumulado 2026-30 (€m)", ctrl(5), f"=SUM({LBO}!N58:R58)", "#,##0"),
        ("Cheque en efectivo del sponsor (€m)", ctrl(6), f"={LBO}!E208", "#,##0"),
        ("Dividendo del recap (€m)", "0", f"=-SUM({LBO}!N153:R153)", "#,##0"),
    ]
    for i, (lab, base, live, fmt) in enumerate(rows):
        r = 8 + i
        ws[f"B{r}"] = lab
        ws[f"C{r}"] = f"={base}" if not base.startswith("=") else base
        ws[f"D{r}"] = live
        ws[f"E{r}"] = f"=D{r}-C{r}"
        for c in "CDE":
            ws[f"{c}{r}"].number_format = fmt
        ws[f"D{r}"].font = BOLD
    ws["B16"] = "«Sin palancas» es el caso operativo elegido sin el plan; «Con palancas» es el modelo en vivo."
    ws["B16"].font = Font(italic=True, color="FF52514E", size=9)

    r = inp["contrib_row"]
    ws[f"B{r}"] = "Contribución de cada palanca"
    ws[f"B{r}"].font = Font(bold=True, size=12)
    r += 1
    for col, text in zip("BCDE", ["Palanca", "Δ ventas 2030", "Δ EBITDA 2030", "Capex 26-30"]):
        ws[f"{col}{r}"] = text
        ws[f"{col}{r}"].font = BOLD
        ws[f"{col}{r}"].fill = HEAD_FILL
    r += 1
    for key, (rr, re, rc) in f["contrib"].items():
        ws[f"B{r}"] = L.LEVER_BY_KEY[key].name
        ws[f"C{r}"] = f"=Palancas_calc!H{rr}" if rr else "-"
        ws[f"D{r}"] = f"=Palancas_calc!H{re}" if re else "-"
        ws[f"E{r}"] = f"=SUM(Palancas_calc!D{rc}:H{rc})" if rc else "-"
        for c in "CDE":
            ws[f"{c}{r}"].number_format = "#,##0"
        r += 1
    ws[f"B{r}"] = "Circulante: caja liberada acumulada"
    ws[f"E{r}"] = f"=Palancas_calc!C{f['wc_cash']}"
    ws[f"E{r}"].number_format = "#,##0"
    r += 1
    ws[f"B{r}"] = "PropCo: caja recibida al cierre"
    ws[f"E{r}"] = f"={f['proceeds']}"
    ws[f"E{r}"].number_format = "#,##0"

    from openpyxl.chart.series import SeriesLabel

    chart = LineChart()
    chart.title = "EBITDA pre-IFRS 16 (€m)"
    chart.height, chart.width = 7.5, 16
    calc = ws.parent["Palancas_calc"]
    for row, title, color in [(f["base_rows"]["ebitda"], "Sin palancas", "898781"),
                              (f["fin"]["ebitda"], "Con palancas", "2A78D6")]:
        chart.add_data(Reference(calc, min_col=3, max_col=8, min_row=row, max_row=row), from_rows=True,
                       titles_from_data=False)
        s_ = chart.series[-1]
        s_.tx = SeriesLabel(v=title)
        s_.graphicalProperties.line.solidFill = color
        s_.graphicalProperties.line.width = 28000
        s_.smooth = False
    chart.set_categories(Reference(calc, min_col=3, max_col=8, min_row=3, max_row=3))
    chart.y_axis.numFmt = "#,##0"
    ws.add_chart(chart, "R4")
