# sw_import_code

Addon para Odoo 19 orientado a importaciones con reglas de matching por código, usando herencia (sin modificar código base).

## Objetivo

Aplicar comportamiento de importación robusto y mantenible:

### 1) `product.supplierinfo`
En contexto de import:

1. Busca registro existente por:
   - `partner_id` + `product_code` (código de producto del proveedor).
2. Si existe, **actualiza** ese supplierinfo.
3. Si no existe, intenta resolver `product.template` por:
   - referencia interna (`default_code`) en columnas auxiliares (`product_default_code`, `default_code`, `x_product_code`)
   - fallback por nombre (`product_name`, `x_product_name`, `name`)
4. Si no puede resolver relación de producto, **no crea** supplierinfo.

### 2) `product.template`
En contexto de import:

1. Busca producto por `default_code`.
2. Si no encuentra, busca por `name`.
3. Si encuentra, **actualiza**.
4. Si no encuentra, **crea** nuevo.

## Diseño para minimizar impacto entre versiones

- Implementación por herencia de modelos:
  - `product.template`
  - `product.supplierinfo`
- Sin monkey-patching ni cambios en core.
- Helpers privados `_sw_*` para encapsular lógica de matching y facilitar ajustes mínimos futuros.

## Instalación

1. Copiar `sw_import_code` dentro de addons path.
2. Actualizar lista de apps.
3. Instalar **Softwork Import by Code**.

## Notas

- La detección de contexto import usa flags comunes:
  - `import_file`, `import_mode`, `is_import`, `from_import`.
- Si tu flujo usa otro flag, se puede agregar fácilmente en `_sw_is_import_context()`.
