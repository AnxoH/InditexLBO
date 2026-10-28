"""
pasar_al_excel.py
=================
Pasa los valores del dashboard (botón «Copiar columna») a la hoja Palancas del Excel integrado
sin abrir Excel: lee el portapapeles, comprueba cada valor y lo escribe en las celdas D19:D62.

Solo cambia esas celdas dentro del .xlsx (no lo reescribe con openpyxl, que borraría el gráfico) y
marca el libro para que Excel lo recalcule al abrirlo. Antes guarda una copia en
output/Excel_antes_de_pasar_valores.xlsx.

Uso, desde la carpeta del repositorio y con el Excel cerrado:
    .venv/bin/python "Business Plan/pasar_al_excel.py"              # lee el portapapeles
    .venv/bin/python "Business Plan/pasar_al_excel.py" valores.txt  # o un archivo con la columna
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bp import levers as L  # noqa: E402
from bp.web import FIRST_ROW, YEAR_OPTIONS, excel_rows  # noqa: E402

EXCEL = ROOT.parent / "Excels" / "Inditex_LBO_Rollover50_BusinessPlan.xlsx"
BACKUP = ROOT / "output" / "Excel_antes_de_pasar_valores.xlsx"


def _number(s: str) -> float:
    s = s.strip().replace(" ", "").replace(" ", "")
    if "," in s and "." in s:  # el último separador es el decimal
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    return float(s.replace(",", "."))


def parse_column(text: str) -> tuple[dict, dict]:
    """Convierte la columna copiada (una línea por fila, D19 a D62) en valores e interruptores, y la valida."""
    rows = excel_rows()
    last = rows[-1]["row"]
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if len(lines) != last - FIRST_ROW + 1:
        raise ValueError(f"Se esperaban {last - FIRST_ROW + 1} líneas (celdas D{FIRST_ROW}:D{last}) y hay {len(lines)}. "
                         "Vuelve a pulsar «Copiar columna» en el dashboard.")
    by_row = {x["row"]: x for x in rows}
    params = {(lv.key, p.key): p for lv in L.LEVERS for p in lv.params}
    values, on, errors = L.default_values(), {}, []
    for i, line in enumerate(lines):
        r, s = FIRST_ROW + i, line.strip()
        x = by_row.get(r)
        if x is None:
            if s:
                errors.append(f"D{r} debería estar vacía y trae «{s}»")
            continue
        try:
            v = _number(s)
        except ValueError:
            errors.append(f"D{r}: «{s}» no es un número")
            continue
        if x["param"] is None:
            if v not in (0, 1):
                errors.append(f"D{r} ({L.LEVER_BY_KEY[x['lever']].name}): el interruptor debe ser 0 o 1")
            on[x["lever"]] = v == 1
            continue
        p = params[(x["lever"], x["param"])]
        if p.key == "year" and v not in YEAR_OPTIONS:
            errors.append(f"D{r} ({p.label}): debe ser {', '.join(map(str, YEAR_OPTIONS))}")
        elif p.edges is not None and not p.edges[0] <= v <= p.edges[4]:
            errors.append(f"D{r} ({p.label}): {v:g} está fuera del rango {p.edges[0]:g} - {p.edges[4]:g}")
        values[x["lever"]][x["param"]] = v
    if errors:
        raise ValueError("\n".join(errors))
    return values, on


def _sheet_path(files: dict, name: str) -> str:
    wb = files["xl/workbook.xml"].decode("utf-8")
    tag = re.search(rf'<sheet\b[^>]*\bname="{re.escape(name)}"[^>]*>', wb)
    if tag is None:
        raise ValueError(f"El Excel no tiene la hoja {name}")
    rid = re.search(r'\br:id="([^"]+)"', tag.group(0)).group(1)
    rels = files["xl/_rels/workbook.xml.rels"].decode("utf-8")
    target = re.search(rf'<Relationship\b[^>]*\bId="{rid}"[^>]*>', rels).group(0)
    target = re.search(r'\bTarget="([^"]+)"', target).group(1)
    return target.lstrip("/") if target.startswith("/") else "xl/" + target


def _set_number(xml: str, ref: str, value: float) -> str:
    cell = re.compile(rf'<c r="{ref}"(?P<attrs>[^>]*?)(?:/>|>.*?</c>)', re.S)
    m = cell.search(xml)
    if m is None:
        raise ValueError(f"No encuentro la celda {ref} en la hoja Palancas")
    attrs = re.sub(r'\s+t="[^"]*"', "", m.group("attrs"))  # número, no texto ni fórmula
    v = int(value) if float(value).is_integer() else value
    return xml[:m.start()] + f'<c r="{ref}"{attrs}><v>{v!r}</v></c>' + xml[m.end():]


def _full_calc_on_load(wb: str) -> str:
    if "<calcPr" in wb:
        return re.sub(r"<calcPr\b([^>]*?)(\s*/?)>",
                      lambda m: "<calcPr" + re.sub(r'\s+fullCalcOnLoad="[^"]*"', "", m.group(1))
                      + ' fullCalcOnLoad="1"' + m.group(2) + ">", wb, count=1)
    anchor = "</definedNames>" if "</definedNames>" in wb else "</sheets>"
    return wb.replace(anchor, anchor + '<calcPr fullCalcOnLoad="1"/>', 1)


def write_to_excel(values: dict, on: dict, path: Path = EXCEL, backup: Path | None = BACKUP) -> Path:
    """Escribe interruptores y parámetros en la columna D de la hoja Palancas, sin tocar nada más."""
    cells = {}
    for x in excel_rows():
        cells[x["row"]] = (1 if on[x["lever"]] else 0) if x["param"] is None else values[x["lever"]][x["param"]]
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        files = {i.filename: z.read(i.filename) for i in infos}
    sheet = _sheet_path(files, "Palancas")
    xml = files[sheet].decode("utf-8")
    for r, v in cells.items():
        xml = _set_number(xml, f"D{r}", v)
    files[sheet] = xml.encode("utf-8")
    files["xl/workbook.xml"] = _full_calc_on_load(files["xl/workbook.xml"].decode("utf-8")).encode("utf-8")

    if backup is not None:
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(suffix=".xlsx", dir=path.parent)
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for i in infos:
            z.writestr(i, files[i.filename])
    os.replace(tmp, path)
    return path


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Pasa los valores del dashboard a la hoja Palancas del Excel.")
    ap.add_argument("archivo", nargs="?", help="archivo con la columna copiada (por defecto, el portapapeles)")
    ap.add_argument("--excel", type=Path, default=EXCEL, help="Excel integrado de destino")
    args = ap.parse_args(argv)
    text = (Path(args.archivo).read_text(encoding="utf-8") if args.archivo
            else subprocess.run(["pbpaste"], capture_output=True, text=True, check=True).stdout)
    try:
        values, on = parse_column(text)
    except ValueError as e:
        sys.exit(f"No he cambiado el Excel:\n{e}")
    write_to_excel(values, on, args.excel)
    for lv in L.LEVERS:
        bands = [p.band(values[lv.key][p.key]) for p in lv.params if p.edges is not None]
        state = "activa " if on[lv.key] else "apagada"
        print(f"  {state}  {lv.name}" + (f"  ({', '.join(bands)})" if on[lv.key] and bands else ""))
    print(f"\nHecho: {args.excel.name}, hoja Palancas, celdas D{FIRST_ROW}:D{excel_rows()[-1]['row']}.")
    print(f"Copia del Excel anterior en {BACKUP.relative_to(ROOT.parent)}. Ábrelo en Excel: se recalcula al abrir.")


if __name__ == "__main__":
    main()
