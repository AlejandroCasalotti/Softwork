import csv
import io


def parse_reserves(content):
    if len(content) > 1024 * 1024:
        raise ValueError("El archivo supera 1 MB.")
    text = content.decode("utf-8-sig")
    if not text.strip():
        raise ValueError("El archivo está vacío.")
    delimiter = ";" if ";" in text.splitlines()[0] else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames or "reserve_qty" not in reader.fieldnames or not {"sku", "default_code"}.intersection(reader.fieldnames):
        raise ValueError("La plantilla debe contener sku y reserve_qty.")
    rows, errors, seen = [], [], set()
    for number, row in enumerate(reader, 2):
        sku = (row.get("sku") or row.get("default_code") or "").strip()
        raw = (row.get("reserve_qty") or "").strip()
        if not sku or not raw.isascii() or not raw.isdecimal():
            errors.append(f"Fila {number}: SKU vacío o reserva inválida (se requiere un entero no negativo).")
        elif sku in seen:
            errors.append(f"Fila {number}: SKU duplicado {sku}.")
        else:
            seen.add(sku)
            rows.append((sku, int(raw)))
        if number > 10001:
            raise ValueError("La importación admite hasta 10.000 filas.")
    if errors:
        raise ValueError("No se importó ninguna fila. " + " ".join(errors[:8]))
    if not rows:
        raise ValueError("El archivo no contiene reservas.")
    return rows