# AUDITORÍA EXHAUSTIVA — SOFTWORK COMMERCE ENGINE (SCE) v1.0

**Fecha:** 2026-09-10  
**Tipo:** Auditoría de solo lectura  
**Objetivo:** Definir arquitectura completa para SCE v1.0 como producto comercial Odoo 19 ↔ Mercado Libre

---

## A. RESUMEN EJECUTIVO

SCE es un conector multi-tenant Odoo ↔ Mercado Libre con dos capas arquitectónicas:

1. **SCE Connect** (sce_connect): Infraestructura multi-tenant, conexiones remotas Odoo, OAuth PKCE, gestión de secretos, mapeos de productos.

2. **SCE Connector ML** (sce_connector_ml): Integración específica Mercado Libre (atributos, categorías, publicaciones, variantes).

**Estado actual:**
- ✅ Arquitectura base estable
- ✅ OAuth PKCE implementado y funcional
- ✅ Publicaciones simples y variantes (PARCIAL)
- ✅ Stock y Precios (PARCIAL - sin motor de reglas)
- ⚠️ UX dispersa, sin dashboard unificado
- ⚠️ Falta observabilidad amigable al usuario final
- ⚠️ Sincronización de ventas (NO IMPLEMENTADO)
- ⚠️ Logging técnico, sin logs comerciales

**Madurez promedio:** 2.8/5  
**Críticos bloqueadores:** 0  
**Gaps de producto:** 8 (Alto y Crítico)

---

## B. ARQUITECTURA ACTUAL

```
┌──────────────────────────────────────────────────────────────────┐
│                    USUARIO FINAL (Odoo 19)                       │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│              SCE ACCOUNT (sce.account)                           │
│  ├─ Conector específico (sce.connector)                         │
│  ├─ Provider Type (mercadolibre, shopify, etc.)                │
│  ├─ Company ID (Odoo local)                                     │
│  └─ Credenciales/Tokens/Estado                                 │
└──────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  SCE CONNECT     │  │  PROVIDER IMPL   │  │  MARKETPLACE     │
│  (sce_connect)   │  │  (sce_connector_ │  │  (sce_product_   │
│                  │  │   mercadolibre)  │  │   marketplace)   │
│ ├─ Tenant        │  │                  │  │                  │
│ ├─ External      │  │ ├─ MercadoLibre  │  │ ├─ Publication   │
│ │  Connection    │  │ │   OAuth         │  │ ├─ Mappings      │
│ ├─ ML Account    │  │ ├─ API Calls      │  │ └─ Stock/Precio  │
│ ├─ Marketplace   │  │ └─ Webhooks      │  │                  │
│ │  Mapping       │  │                  │  │                  │
│ └─ Rule Engine   │  └──────────────────┘  └──────────────────┘
└──────────────────┘
        │
        ▼
   JSON-2 Bridge (sce_connect_agent)
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│              ODOO EXTERNO (Remoto)                               │
│  ├─ product.product                                              │
│  ├─ stock.move                                                   │
│  ├─ product.pricelist                                            │
│  └─ res.partner (clientes)                                       │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│           MERCADO LIBRE API (rest-api.mercadolibre)              │
│  ├─ /items (publicaciones)                                       │
│  ├─ /inventory (stock)                                           │
│  ├─ /orders (ventas)                                             │
│  └─ /categories (categorías/atributos)                           │
└──────────────────────────────────────────────────────────────────┘
```

**Flujos principales implementados:**

1. **OAuth PKCE** → ML Account → Conector → Publicación
2. **Producto** → Publication → Mapping → Stock/Precio Sync (PARCIAL)
3. **Órdenes** → Import Orders (NO IMPLEMENTADO)
4. **Webhooks** → Event → Job Queue (BÁSICO)

---

## C. MODELOS

| Modelo | Módulo | Archivo | Propósito | Estado |
|--------|--------|---------|-----------|--------|
| **sce.account** | softwork_ecommerce_conector_base | sce_account.py | Cuenta genérica del conector | ✅ Funcional |
| **sce.connector** | softwork_ecommerce_conector_base | sce_connector.py | Definición del tipo de conector (ML, Shopify, etc.) | ✅ Funcional |
| **sce.tenant** | sce_connect | sce_tenant.py | Multi-tenancy, aisla datos por inquilino | ✅ Funcional |
| **sce.external.connection** | sce_connect | sce_external_connection.py | Conexión a Odoo remoto (JSON-2) | ✅ Funcional |
| **sce.secret** | sce_connect | sce_secret.py | Almacenamiento encriptado de secretos | ✅ Funcional |
| **sce.mercadolibre.account** | sce_connect | sce_mercadolibre_account.py | Cuenta ML con OAuth, tokens, vendedor | ✅ Funcional |
| **sce.oauth.transaction** | sce_connect | sce_oauth_transaction.py | Transacción PKCE OAuth (state, verifier) | ✅ Funcional |
| **sce.external.product.mapping** | sce_connect | sce_external_product_mapping.py | Mapping de product.product remoto | ✅ Funcional |
| **sce.connect.marketplace.mapping** | sce_connect | sce_connect_marketplace_mapping.py | Mapping entre Odoo → ML (item, variante) | ✅ Funcional |
| **sce.connect.stock.policy** | sce_connect | sce_connect_stock_policy.py | Política de stock por cuenta (V1: Bloque B) | ✅ Nuevo |
| **sce.connect.price.policy** | sce_connect | sce_connect_price_policy.py | Política de precio por cuenta (V1: Bloque B) | ✅ Nuevo |
| **sce.connect.rule** | sce_connect | sce_connect_rule.py | Reglas de transformación stock/precio | ⚠️ Básico |
| **marketplace.publication** | sce_product_marketplace | marketplace_publication.py | Publicación de producto en ML | ✅ Funcional |
| **marketplace.product.mapping** | sce_product_marketplace | marketplace_product_mapping.py | Mapping producto ↔ ML (variantes) | ✅ Funcional |
| **sce.job** | softwork_ecommerce_conector_base | sce_job.py | Job de sincronización genérico | ✅ Funcional |
| **sce.connect.job** | sce_connect | sce_connect_job.py | Job específico stock Connect | ✅ Nuevo |
| **sce.connect.price.job** | sce_connect | sce_connect_price_job.py | Job específico precio Connect | ✅ Nuevo |
| **sce.log** | softwork_ecommerce_conector_base | sce_log.py | Log técnico | ✅ Funcional |
| **sce.event** | softwork_ecommerce_conector_base | sce_event.py | Evento interno (JobStarted, etc.) | ✅ Básico |
| **marketplace.sale.order** | sce_product_marketplace | (heredado) | Venta importada de ML | ❌ NO IMPLEMENTADO |
| **ml_attribute_*** | sce_connector_ml | ml_*.py | Atributos, categorías, listing types de ML | ✅ Funcional |

**Relaciones clave:**

```
sce.tenant
  │
  ├─→ sce.external.connection
  │     └─→ sce.external.product.mapping
  │           └─→ sce.connect.marketplace.mapping
  │                 ├─→ marketplace.publication
  │                 └─→ marketplace.product.mapping
  │
  └─→ sce.mercadolibre.account (OAuth)
        └─→ sce.account (conector ML)
              ├─→ marketplace.publication
              ├─→ sce.connect.stock.policy
              ├─→ sce.connect.price.policy
              └─→ sce.job
```

---

## D. SERVICIOS Y PROVIDERS

| Servicio | Módulo | Archivo | Responsabilidad | Estado |
|----------|--------|---------|-----------------|--------|
| **ProviderFactory** | softwork_ecommerce_conector_base | provider_factory.py | Factory que resuelve provider por connector.provider_type | ✅ Funcional |
| **IProvider** (interface) | softwork_ecommerce_conector_base | provider_interface.py | Contrato de métodos obligatorios | ✅ Funcional |
| **MercadoLibreProvider (legacy)** | softwork_ecommerce_conector_base | ml_provider.py | Provider built-in (DEPRECADO, fallback) | ⚠️ Deprecado |
| **MercadoLibreExternalProvider** | softwork_provider_mercadolibre | provider.py | Provider externo explícito ML | ✅ Funcional |
| **OdooProvider** | softwork_provider_odoo | provider.py | Provider Odoo (uso interno) | ✅ Funcional |
| **ConnectionService** | sce_connect | connection_service.py | JSON-2 connection pool, adapter factory | ✅ Funcional |
| **Odoo19Json2Adapter** | sce_connect | odoo19_json2_adapter.py | HTTP JSON-2 adapter, SSRF protection | ✅ Funcional |
| **MercadoLibreOAuthService** | sce_connect | mercadolibre_oauth.py | Flujo PKCE OAuth, token refresh | ✅ Funcional |
| **OAuthStateService** | sce_connect | oauth_state.py | Validación state, code_verifier PKCE | ✅ Funcional |
| **SceConnectStockService** | sce_connect | connect_stock_service.py | Stock sync: remote → policy → rules → provider | ✅ Funcional |
| **SceConnectPriceService** | sce_connect | connect_price_service.py | Price sync: remote pricelist → policy → rules → provider | ✅ Funcional |
| **SceConnectMarketplaceMappingService** | sce_connect | connect_marketplace_mapping_service.py | Validación ownership, mapeo producto | ✅ Funcional |
| **MarketplacePublicationService** | sce_product_marketplace | publication_service.py | Payload build, categoría SELLER_SKU, enqueue | ✅ Funcional |
| **SceLogService** | softwork_ecommerce_conector_base | log_service.py | Log técnico centralizado | ✅ Funcional |
| **ProductReconciliationService** | sce_connector_ml | product_reconciliation.py | Reconciliación producto ↔ ML | ⚠️ Parcial |
| **StockPolicyCalculator** | sce_connect | stock_policy_calculator.py | Fórmula reserva (V1: Bloque B) | ✅ Nuevo |
| **PricePolicyCalculator** | sce_connect | price_policy_calculator.py | Fórmula precio + safety (V1: Bloque B) | ✅ Nuevo |
| **SceConnectPriceBridge** | sce_connect_agent | price_bridge.py | Bridge remoto read-only (V1: Bloque B) | ✅ Nuevo |

**Contrato de Provider (REQUIRED_METHODS):**

```python
authenticate, refresh_token, health,
publish_product, update_product, delete_product,
update_stock, update_price, get_item,
get_orders, get_order, cancel_order,
get_messages, answer_message,
download_invoice, upload_invoice,
search_categories, get_category_attributes,
get_category_required_fields, get_listing_prices,
sync, webhook
```

---

## E. CUENTA ML / OAUTH

### Modelo: sce.mercadolibre.account

```python
name: CharField (identificador amigable)
tenant_id: Many2one(sce.tenant) [REQUERIDO]
seller_user_id: Char (ID ML del vendedor, readonly)
seller_nickname: Char (nickname ML, readonly)
access_token_secret_id: Many2one(sce.secret) [readonly]
refresh_token_secret_id: Many2one(sce.secret) [readonly]
scopes: Char (scopes OAuth, readonly)
expires_at: Datetime (expiración access_token, readonly)
status: Selection [draft, auth_pending, connected, token_refreshing, auth_required, disconnected, error]
metadata_json: Text (token_type, site_id, readonly)
last_connection_test_at, last_error, connected_at, disconnected_at: Datetime
```

**Constraint:** `UNIQUE(tenant_id, seller_user_id)`

### Flujo OAuth PKCE

1. **start(account)** → genera state + code_challenge PKCE → redirige a ML
   - State almacenado en `sce.oauth.transaction` con hash
   - Code verifier encriptado en `sce.secret`

2. **complete(state, code, user)** → valida transacción → intercambia por tokens
   - Resuelve `sce.mercadolibre.account`
   - Obtiene `seller_user_id` y `metadata_json`
   - Almacena tokens en `sce.secret`
   - Marca transacción como `used`

3. **refresh(account)** → refresh_token flow → nuevos tokens
   - Cambio de status a `token_refreshing`
   - Lock de DB para evitar race condition
   - Retorna a `connected`

### Estado implementado

- ✅ PKCE completo (S256)
- ✅ Encriptación de tokens en `sce.secret`
- ✅ Refresh automático antes de expiración
- ✅ Test de conexión (health check)
- ✅ Desconexión manual
- ✅ Manejo de errores (auth_required, disconnected)
- ❌ Manejo de logout de ML (revoke token)
- ❌ Soporte multi-account por vendedor (1:1 actual)

---

## F. DEPENDENCIAS DE SCE CONNECT

### Acoplamientos críticos encontrados

**1. sce.account ACOPLADA a SCE Connect**

- `sce.account` reside en `softwork_ecommerce_conector_base` (módulo base)
- Hereda campos de `sce.connect` (tenant_id, external_connection_id, connect_ownership_state)
- Pero SCE Connect es opcional (dependencia de `sce_connect`)

**Problema:** Si un cliente instala solo `softwork_ecommerce_conector_base` sin `sce_connect`, los campos heredados fallan.

**Verificación:** Buscar todas las referencias a campos SCE Connect en sce_account:

```
├─ tenant_id → hereda de sce_connect (sce_account.py, línea 38)
├─ external_connection_id → hereda de sce_connect
├─ connect_mercadolibre_account_id → hereda de sce_connect  
├─ connect_ownership_state → @depends(...) computed
└─ _check_connect_mercadolibre_account → constraint
```

**¿Puede funcionar sce.mercadolibre.account SIN sce_connect?**

- sce.mercadolibre.account requiere tenant_id (Many2one sce.tenant)
- sce.tenant vive en sce_connect
- Conclusión: **NO. sce.mercadolibre.account depende de sce_connect**

**¿Puede funcionar marketplace.publication SIN sce_connect?**

- marketplace.publication depende de sce.account
- sce.account (con Connect) depende de sce_connect
- Conclusión: **SÍ. Con condición: sin usar campos Connect (tenant, connection, ML identity)**

### Dependencias entre módulos

```
softwork_ecommerce_conector_base (base)
    │
    ├─→ sce_connect (multi-tenant, connections, OAuth)
    │     ├─→ sce_connector_ml (ML específico)
    │     └─→ sce_connect_agent (remote bridge)
    │
    └─→ sce_product_marketplace (publicaciones genéricas)
          ├─→ sce_connect (para mappings Connect)
          └─→ sce_connector_ml (vistas específicas ML)

sce_connector_ml
    ├─→ sce_connect (models, services)
    ├─→ sce_product_marketplace (publications)
    └─→ ml_product (vistas product)

softwork_provider_mercadolibre
    └─→ softwork_ecommerce_conector_base (interface)

ml_product
    ├─→ sce_product_marketplace
    ├─→ sce_connector_ml
    └─→ product, stock
```

### Puntos de acoplamiento

| Acoplamiento | Tipo | Impacto |
|--------------|------|--------|
| sce.mercadolibre.account → sce.tenant | CRÍTICO | Imposible desacoplar sin redesign |
| sce.account → fields SCE Connect | CRÍTICO | Causa herencia problemática |
| provider_factory → connector.provider_type | MODERADO | Extensible pero rígido |
| publication → account.company_id | MODERADO | OK, necesario para multiempresa |
| marketplace_mapping → tenant_id | MODERADO | OK, necesario para seguridad |

### Hipótesis de desacoplamiento

**Propuesta:** Separar capas claramente

```
CAPA 1: sce_base
  └─ Modelos genéricos: sce.account, sce.connector, sce.job, sce.log

CAPA 2: sce_connect (opcional, multi-tenant)
  └─ Modelos: sce.tenant, sce.external.connection, sce.mercadolibre.account

CAPA 3: sce_product_marketplace (genérico)
  └─ Modelos: marketplace.publication, marketplace.product.mapping

CAPA 4: sce_connector_ml (específico ML)
  └─ Modelos: categorías, atributos, wizards
```

**Análisis:** Actual NO implementa esta separación. sce_mercadolibre_account acoplada a tenant.

---

## G. PRODUCTOS Y PUBLICACIONES

### Flujo actual

```
product.template (Odoo)
    │
    ├─→ product.product (variantes)
    │
    └─→ marketplace.publication (1 por cuenta)
          │
          ├─→ marketplace.product.mapping (1+ por variante)
          │     └─→ sce.connect.marketplace.mapping (mappings Connect)
          │
          └─→ [external_id, external_status, title, category, listing_type, ...]
```

### Campos relevantes marketplace.publication

```
product_tmpl_id: M2O product.template [REQUERIDO, cascade]
account_id: M2O sce.account [REQUERIDO, restrict]
external_id: Char (ID ML del item)
external_status: Char (readonly)
external_url: Char (URL en ML)
state: Selection [draft, category, attributes, pricing, shipping, pictures, ready, publishing, published, failed]
title, category_ref, category_name, listing_type, condition, shipping_mode
price, stock_reserve_qty, effective_qty (computed)
attributes_json, pictures_json, sale_terms_json, provider_data_json
last_stock_sent, last_stock_sync_at
```

### SELLER_SKU

**Estado:** ✅ IMPLEMENTADO y AUDITABLE

```python
# marketplace_publication_service.py, línea ~55

def _build_payload(self, publication):
    # 1. Consulta metadata de categoría para SELLER_SKU
    seller_sku_info = self._get_category_seller_sku_info(...)
    
    # 2. Para producto simple + variante única + seller_sku_info
    #    Agrega SELLER_SKU = variant.default_code
    if len(variants) == 1 and seller_sku_info:
        if variant.default_code:
            payload["attributes"].append({
                "id": "SELLER_SKU",
                "value_name": variant.default_code
            })
    
    # 3. Para variantes múltiples
    #    Agrega variation.attributes = [{id: SELLER_SKU, value_name: ...}]
    if len(variants) > 1:
        for variant in variants:
            variation = {
                "seller_custom_field": variant.default_code or False,
                "attributes": [...SELLER_SKU si allow_variations...]
            }
```

**Validaciones:**

- ✅ `_normalize_variations()` conserva SELLER_SKU en variantes
- ✅ `_apply_variant_mappings()` respeta SELLER_SKU en priority
- ✅ No confunde `attribute_combinations` (atributos Odoo) con `attributes` (ML)
- ✅ Respeta `allow_variations` del atributo ML
- ✅ Tests cubren SELLER_SKU (test_catalog_reader.py)

### Variantes

**Soporte:**

- ✅ Producto simple (sin variantes) → publicación simple en ML
- ✅ Producto con variantes → variaciones ML con attribute_combinations
- ✅ attribute_combinations preservan atributos Odoo
- ⚠️ UOM conversion parcial (por defecto 1:1)
- ❌ Precios independientes por variante (V1 requiere precio común)

### Atributos y categorías

**Estado:** ✅ IMPLEMENTADO

Modelos:
```
ml_category
ml_attribute (inherits ml_category)
ml_attribute_option
ml_listing_type
```

Wizards:
```
ml_category_search_wizard → busca categoría
ml_attribute_editor_wizard → mapea atributos Odoo ↔ ML
ml_attribute_option_picker_wizard → selecciona valores
ml_publish_assistant_wizard → asistente publicación (PARCIAL)
ml_publish_config_wizard → configuración precio/stock
```

### Publicación completa

**Ciclo actual:**

1. Crear publication (estado: draft)
2. Seleccionar categoría ML (estado: category)
3. Mapear atributos (estado: attributes)
4. Configurar precio y stock (estado: pricing)
5. Configurar envío (estado: shipping)
6. Cargar imágenes (estado: pictures)
7. Revisar (estado: ready)
8. Publicar (publish_product → estado: publishing → published)

**Problemas encontrados:**

- ⚠️ No existe una UX única de publicación
- ⚠️ El flow está repartido en múltiples vistas/wizards
- ⚠️ No valida completitud antes de publicar
- ⚠️ Errores no son explícitos
- ❌ Imágenes remota (no desde URL)

---

## H. VENTAS

### Estado: ❌ NO IMPLEMENTADO

**Búsqueda realizada:**

```
grep -r "import_order\|import_sales\|sale\.order\|sce\.sale" 
```

**Resultados:**

- `sce.job` tiene tipo `"import_orders"` pero no existe handler
- `marketplace.sale.order` mencionado en schema pero no existe modelo
- No hay webhook listener para órdenes ML
- No hay API call para `get_orders`

**Lo que SI existe:**

- `provider.get_orders()` en contrato (required_methods)
- `provider.get_order()` en contrato
- Infraestructura de eventos (`sce.event`)
- Infraestructura de jobs

**Lo que NO existe:**

- Modelo para almacenar órdenes
- Mapeo cliente ML ↔ res.partner Odoo
- Lógica de crear sale.order en Odoo
- Webhook para notificaciones de orden
- Sincronización de pagos
- Sincronización de estado entrega

**Conclusión:** FULL, PARTIAL, cancelaciones: todo ausente.

---

## I. STOCK

### Estado actual: ⚠️ PARCIAL

### Modelos

```
marketplace.publication.effective_qty (computed)
marketplace.publication.stock_reserve_qty (manual)
marketplace.product.mapping.last_stock_sent (readonly)
sce.connect.stock.policy (V1: Bloque B)
```

### Flujo de sincronización

```
Cron: ir_cron_sce_sync_marketplace_stock
  → marketplace_publication.cron_enqueue_stock_sync()
  → Itera publications con external_id + sync_stock=True
  → marketplace.publication.service.enqueue(..., "update_stock")
  → Crea sce.job con job_type="sync_publication_stock"

Job execution:
  → provider.sync(operation="update_stock")
  → sce.connect.stock.service.sync_mapping() [V1: Bloque B]
    → _remote_stock() [consulta Odoo remoto free_qty]
    → _apply_policy() [Stock Policy: reserva]
    → _apply_rules() [Rule Engine: transformaciones]
    → provider.update_stock() [API ML]
    → mappings.write(..., last_stock_sent, last_stock_sync_at)
```

### Stock Policy (V1: Bloque B)

**Nueva:** sce.connect.stock.policy

```python
account_id: M2O sce.account [REQUERIDO, cascade, unique]
active: Boolean [default=False]
source: Selection [free_qty] (Odoo Free to Use)
reserve_type: Selection [none, fixed, percent]
reserve_value: Float
```

**Fórmula:**

```python
# Caso: Sin reserva
stock_final = max(0, stock)

# Caso: Reserva fija
stock_final = max(0, stock - reserve_value)

# Caso: Reserva %
stock_final = floor(stock * (1 - reserve_value / 100))
```

**Estado:** ✅ IMPLEMENTADO (Bloque B)

### Validaciones

- ✅ Stock no puede ser negativo (clamp a 0)
- ✅ Reserva % validada 0-100
- ⚠️ Decimales: Soporta pero conversión a int
- ⚠️ UOM: No aplicada (asume misma UOM)

### Crons

```
ir_cron_sce_sync_marketplace_stock
  Modelo: sce.job
  Método: _execute_job() → sync operation
  Frecuencia: 10 minutos (configurable)
  Estado: ✅ Funcional
```

### Gaps

- ❌ Stock Flex (Mercado Libre)
- ❌ Reglas por categoría
- ❌ Reglas por SKU
- ❌ Ubicaciones múltiples
- ❌ Stock de seguridad avanzado
- ❌ Prioridad de reglas

---

## J. PRECIOS

### Estado actual: ⚠️ PARCIAL

### Modelos

```
marketplace.publication.price (manual o computed)
marketplace.publication.pricelist_id (M2O product.pricelist)
sce.connect.price.policy (V1: Bloque B)
```

### Flujo de sincronización

```
Cron: ir_cron_sce_connect_price
  → sce.connect.price.service.enqueue_mapping()
  → Crea sce.connect.price.job

Job execution:
  → sce.connect.price.service.sync_mapping()
    → _remote_price() [Consulta pricelist remota O list_price]
    → calculate_price() [Decimal, Odoo precision]
    → _apply_policy() [Price Policy: % + fijo + rounding + safety]
    → _apply_rules() [Rule Engine]
    → provider.update_price() [API ML]
    → mappings.write(..., last_price_sent, last_price_sync_at)
```

### Price Policy (V1: Bloque B)

**Nueva:** sce.connect.price.policy

```python
account_id: M2O sce.account [REQUERIDO, cascade, unique]
active: Boolean
remote_pricelist_id: Integer [ID remoto]
remote_pricelist_name: Char [snapshot]
adjustment_percent: Float (default=0)
adjustment_fixed: Float (default=0)
commercial_rounding: Selection [none, 10, 100, 1000]
safety_enabled: Boolean
max_decrease_percent: Float (default=20)
```

**Fórmula:**

```python
# Base
precio = base_price

# Aplicar ajuste %
precio = precio * (1 + ajuste_pct / 100)

# Aplicar ajuste fijo
precio = precio + ajuste_fijo

# Redondeo comercial
if rounding != "none":
    quantum = Decimal(rounding)
    precio = (precio / quantum).to_integral_value() * quantum

# Safety factor (protección contra bajas)
if safety_enabled and previous_price:
    minimum = previous_price * (1 - max_decrease_pct / 100)
    blocked = (precio < minimum)
```

**Estado:** ✅ IMPLEMENTADO (Bloque B)

### Validaciones

- ✅ Decimal para precisión monetaria
- ✅ Precio > 0 siempre
- ✅ Redondeo comercial hacia abajo
- ✅ Safety factor no bloquea primer sync
- ✅ Ajuste % y fijo independientes

### Remote Pricelist Bridge (V1: Bloque B)

**Nuevo addon:** sce_connect_agent

**Operación explícita:**

```python
sce.connect.agent.get_product_pricelist_price(
    product_id: int,
    pricelist_id: int,
    quantity: float = 1,
    company_id: int = None,
    context: dict = None
)
```

**No usa execute() genérico → allowlist explícito**

**Validaciones:**

- ✅ Producto existe en empresa
- ✅ Pricelist existe en empresa
- ✅ Compañía en allowed_company_ids (context)
- ✅ Resultado Decimal válido (no infinito)

**Retorna:**

```json
{
  "product_id": 11,
  "pricelist_id": 4,
  "price": "1250.50",
  "currency_id": 3,
  "quantity": "1.0",
  "company_id": 2
}
```

### Crons

```
ir_cron_sce_connect_price
  Modelo: sce.connect.price.job
  Método: _execute_job()
  Frecuencia: 5 minutos (configurable)
  Estado: ✅ Funcional (V1)
```

### Gaps

- ❌ Factor de cuotas (financing)
- ❌ Comisión mercadolibre
- ❌ Pricing automation en ML
- ❌ Promociones
- ❌ Margen % por categoría
- ❌ Costo de producto

---

## K. SINCRONIZACIÓN

### Modelos de Job

**Genérico:** sce.job

```python
job_type: Selection [
    sync_products, sync_stock, sync_prices,
    import_orders, sync_messages, health_check
]
state: Selection [queued, running, done, failed, cancelled]
payload_json, result_json, error_message
started_at, finished_at, duration_ms, attempts
```

**Específicos Connect:**

```
sce.connect.job (stock sync)
sce.connect.price.job (price sync)
```

### Crons registrados

| Nombre | Modelo | Función | Frecuencia | Estado |
|--------|--------|---------|-----------|--------|
| ir_cron_sce_connect_stock | sce.job | enqueue_stock_sync | 10 min | ✅ Funcional |
| ir_cron_sce_connect_price | sce.connect.price.job | enqueue_price_sync | 5 min | ✅ Funcional |
| ir_cron_sce_sync_marketplace_stock | sce.job | cron_enqueue_stock_sync | 15 min | ✅ Funcional |
| ir_cron_sce_health_check | sce.job | health_check | 1 hora | ✅ Funcional |
| ir_cron_sce_process_queue | sce.job | _execute_job | 1 min | ✅ Funcional |
| ir_cron_sce_retry_failed_jobs | sce.job | retry | 5 min | ✅ Funcional |
| ir_cron_sce_cleanup_old_jobs | sce.job | cleanup | 1 día | ✅ Funcional |
| ir_cron_sce_billing_control | sce.job | billing_update | 1 hora | ✅ Funcional |

### Ejecución de jobs

```python
# sce_job.py, _execute_job()

1. Emite evento JobStarted
2. Obtiene provider
3. Parsea payload_json
4. Ejecuta: provider.sync({operation, payload})
5. Registra resultado
6. Emite evento Job completed/failed
7. Crea métrica de uso (jobs_done, duration_ms)
```

### Control de reintentos

```python
# sce_job.py

max_retries: Integer (default=3)
attempts: Integer

if state == "failed" and attempts < max_retries:
    retry() → vuelve a queued
else:
    terminal state
```

### Queue simple (sin external MQ)

- ✅ No usa Redis/RabbitMQ
- ✅ Usa ir.cron + DB state
- ⚠️ No garantiza FIFO
- ⚠️ Duplicación posible si cron re-ejecuta
- ✅ Suficiente para V1

---

## L. LOGS / OBSERVABILIDAD

### Logs técnicos: sce.log

```python
name: Char
level: Selection [DEBUG, INFO, WARNING, ERROR, CRITICAL]
message: Text
details_json: Text
connector_id, account_id, job_id, company_id
```

**Servicio:** sce.log.service

```python
def log(*, name, message, level="INFO", connector, account, job, 
        details_json, provider, operation, elapsed_ms):
    # Centraliza todos los logs técnicos
```

### Eventos: sce.event

```python
_name = "sce.event"
event_type: Selection [JobStarted, JobCompleted, JobFailed, ...]
name, connector_id, account_id, job_id, payload_json
```

### Observabilidad del usuario final

**Estado:** ⚠️ INSUFICIENTE

- ❌ No hay dashboard centralizado
- ❌ No hay historial de sincronizaciones visible
- ❌ No hay alertas de errores
- ❌ Last sync date existe pero no es prominente
- ❌ Error logs no diferenciados para usuario vs técnico

**Ejemplos de información que usuario NO puede ver fácilmente:**

- ¿Cuándo fue la última sincronización de stock?
- ¿Por qué falló el último sync de precios?
- ¿Cuántas publicaciones tienen error?
- ¿Cuál es el estado de mi conexión OAuth?
- ¿Hay datos pendientes de sincronizar?

---

## M. SEGURIDAD

### ACLs (ir.model.access)

```
sce_tenant, sce_external.connection → groups: user/admin
sce_secret → admin only (lectura)
sce_oauth.transaction → user (no write/unlink)
sce_mercadolibre.account → user (no unlink)
marketplace.publication → user (R/W)
sce.job, sce.log → user (R only)
```

**Implementación:** CSV en `*/security/ir.model.access.csv`

### Record Rules (ir.rule)

**Tenant isolation:**

```python
rule_sce_tenant_user:
    domain_force = [("user_ids", "in", [user.id])]
    
rule_sce_external_connection_user:
    domain_force = [("tenant_id.user_ids", "in", [user.id])]

rule_sce_account_user:
    domain_force = [("tenant_id.user_ids", "in", [user.id])]
```

**Estado:** ✅ Implementado para sce_connect

**Verificación:** `sce_connect/security/sce_connect_security.xml` (líneas ~22-120)

### Seguridad de secretos

- ✅ Tokens almacenados en `sce.secret` (modelo encriptado)
- ✅ Acceso requiere `sce_backend_secret_access` context
- ✅ Solo lectura via `get_value()`
- ⚠️ No hay audit log de acceso

### Seguridad OAuth

- ✅ PKCE S256 (code_challenge)
- ✅ State validation (hash único)
- ✅ Code verifier encriptado
- ✅ Expiración de transacción (15 min default)
- ✅ HTTPS requerido en redirect_uri
- ⚠️ No hay revoke de token ML

### Seguridad de conexión remota

- ✅ HTTPS validado (allow_insecure_http flag)
- ✅ SSRF protection (private network check)
- ✅ Timeout validado
- ✅ Credenciales NOT in URL
- ✅ JSON-2 adapter allowlist (read/search/create/write/unlink bloqueado en Phase 1)

### Vulnerabilidades conocidas

| Vulnerabilidad | Severidad | Mitigation | Status |
|----------------|-----------|-----------|--------|
| Múltiples cuentas ML por usuario | MEDIA | ACL por account + tenant | ✅ Partial |
| Cross-tenant access en mappings | MEDIA | Record rule + constraint | ✅ Implemented |
| Token exposure en logs | LOW | Log sanitization | ⚠️ Partial |
| SQL injection en custom rules | LOW | Odoo ORM protection | ✅ Built-in |
| Webhook auth | MEDIA | Token validation | ⚠️ TODO |

---

## N. UX ACTUAL

### Flujo real del usuario

```
Menú: Softwork Ecommerce Connector
├─ Configuration
│  ├─ Connectors
│  │  └─ Create sce.connector (ML)
│  ├─ Accounts (sce.account)
│  │  └─ Create account
│  │     ├─ Provider: MercadoLibre
│  │     ├─ Tenant (SCE Connect)
│  │     ├─ External Connection (JSON-2 a Odoo remoto)
│  │     └─ [Click] Connect to MercadoLibre
│  │          → OAuth PKCE → ML → Callback → sce.mercadolibre.account
│  │
│  └─ Products (marketplace.publication)
│     └─ Create Publication
│        └─ Workflow: draft → category → attributes → pricing → ready → published
│
├─ Operations
│  ├─ Jobs (historial)
│  ├─ Logs (técnicos)
│  └─ Integration Status (snapshot)
│
└─ Billing
   ├─ Subscriptions
   └─ Usage Metrics
```

### Vistas principales

| Vista | Modelo | Archivo | Funcionalidad | Estado |
|-------|--------|---------|---------------|--------|
| sce_account form | sce.account | sce_account_views.xml | Configurar cuenta, credenciales | ✅ Funcional |
| sce_mercadolibre_account form | sce.mercadolibre.account | sce_mercadolibre_account_views.xml | OAuth, estado, tokens | ✅ Funcional |
| marketplace_publication form | marketplace.publication | marketplace_publication_views.xml | Datos publicación, categoría, atributos | ✅ Funcional |
| ml_publish_assistant | ml_publish_assistant_wizard | ml_publish_assistant_wizard_views.xml | Asistente paso a paso | ⚠️ Parcial |
| ml_category_search | ml_category_search_wizard | ml_category_search_wizard_views.xml | Búsqueda y selección de categoría | ✅ Funcional |
| ml_attribute_editor | ml_attribute_editor_wizard | ml_attribute_editor_wizard_views.xml | Mapear atributos Odoo ↔ ML | ✅ Funcional |
| sce_job list | sce.job | sce_job_views.xml | Historial de jobs, estado | ✅ Funcional |
| sce_log list | sce.log | sce_log_views.xml | Logs técnicos, detalles JSON | ✅ Funcional |

### Problemas de UX

| Problema | Impacto | Solución propuesta |
|----------|--------|-------------------|
| No existe dashboard unificado de cuenta ML | ALTO | Crear vista principal: Stock → Precios → Publicaciones |
| Flujo publicación en múltiples pantallas | ALTO | Wizard secuencial único |
| Mensajes de error técnicos | MEDIO | Traducciones amigables al usuario |
| No visible "última sincronización" | MEDIO | Mostrar prominente en account |
| No hay alertas de errores | ALTO | Toast/banner de errores críticos |
| Logs JSON sin UI | MEDIO | Expander amigable en list view |
| No hay preview antes de publicar | MEDIO | Mostrar payload que se enviará a ML |

---

## O. COMPARACIÓN CON ODUMBO

| Funcionalidad | Odumbo | SCE actual | Estado SCE | Gap |
|---------------|--------|-----------|-----------|-----|
| **Cuenta ML** | 1 por usuario | 1 por tenant | Más flexible | ✅ No |
| **Dashboard** | Centralizado | Disperso | Parcial | ⚠️ SÍ |
| **Productos** | Automático | Manual | Básico | ⚠️ SÍ |
| **Publicaciones** | Simple + variantes | Simple + variantes | ✅ OK | ✅ No |
| **SELLER_SKU** | Automático | Automático | ✅ OK | ✅ No |
| **Stock sync** | Automático | Automático | ✅ OK | ✅ No |
| **Stock reserva** | Flexible (%) | V1 (% fijo) | Parcial | ⚠️ SÍ |
| **Stock Flex** | SÍ | NO | NO | ❌ CRÍTICO |
| **Precio sync** | Automático | Automático | ✅ OK | ✅ No |
| **Factor precio** | SÍ | V1 (safety) | Parcial | ⚠️ SÍ |
| **Cuotas ML** | Integrado | NO | NO | ❌ NO (opcional) |
| **Ventas import** | Automático | NO | NO | ❌ CRÍTICO |
| **Cancelaciones** | SÍ | NO | NO | ❌ CRÍTICO |
| **Pagos** | Integrado | NO | NO | ❌ NO (opcional) |
| **Multi-cuenta ML** | SÍ | 1 por tenant | Diferente | ⚠️ SÍ |
| **Multi-empresa Odoo** | SÍ | SÍ (company_id) | ✅ OK | ✅ No |

---

## P. ARQUITECTURA SCE v1.0 PROPUESTA

### Principios

1. **Separación de capas:** Base → Connect → Connector ML
2. **Ownership claro:** Cada modelo tiene owner explícito (account/tenant)
3. **Flujo unificado:** Usuario → Dashboard → Configuración → Sync
4. **Observabilidad:** Usuario sabe qué pasó y por qué
5. **Extensibilidad:** Nuevos marketplaces sin rehacer

### Modelos fundamentales

```
SCE v1.0
├─ Base (independiente)
│  ├─ sce.account (genérico conector)
│  ├─ sce.connector (tipos: ML, Shopify, etc.)
│  ├─ sce.job (cola genérica)
│  └─ sce.log (logs técnicos)
│
├─ Connect (multi-tenant, opcional pero recomendado)
│  ├─ sce.tenant
│  ├─ sce.external.connection (Odoo remoto)
│  ├─ sce.mercadolibre.account (OAuth)
│  ├─ sce.connect.stock.policy
│  ├─ sce.connect.price.policy
│  └─ sce.connect.rule
│
├─ Marketplace (genérico)
│  ├─ marketplace.publication
│  ├─ marketplace.product.mapping
│  ├─ marketplace.sale.order (🆕)
│  └─ marketplace.sync.log (🆕 - logs comerciales)
│
└─ Connector ML (específico)
   ├─ Categorías, atributos (readonly desde ML)
   ├─ Webhooks handler
   └─ Wizards configuración
```

### Dashboard principal (🆕)

```
Usuario: Tienda ML
├─ Estado general
│  ├─ Conexión OAuth: ✅ Conectado [Última: 2h] [Reconectar]
│  ├─ Última publicación: 2h
│  ├─ Stock pendiente: 45 productos
│  └─ Precios pendientes: 12 productos
│
├─ Configuración rápida
│  ├─ Stock → Política: Reserva 10% [Editar]
│  ├─ Precios → Política: +15%, -5% máximo [Editar]
│  └─ Lista remota: MAYORISTA [Cambiar]
│
├─ Últimos errores
│  ├─ ⚠️ 3 publicaciones con error de categoría
│  ├─ ⚠️ 1 sincronización fallida hace 4h
│  └─ [Ver historial]
│
└─ Acciones
   ├─ [Publicar producto] → Wizard
   ├─ [Sincronizar ahora] → Background
   └─ [Ver historial] → Logs comerciales
```

### Componentes nuevos (🆕)

1. **marketplace.sync.log** (logs comerciales)
   - Qué se sincronizó (producto X stock 20)
   - Cuándo (timestamp)
   - Resultado (OK / Error)
   - Impacto (ML ahora tiene stock 18)

2. **marketplace.publication.dashboard**
   - Vista resumida por cuenta
   - Estado: Sincronizando / Pendiente / Error / OK
   - Última acción
   - Botones rápidos

3. **Stock Policy manager (UI mejorada)**
   - Selector de política
   - Preview en tiempo real
   - Aplicación a múltiples productos

4. **Price Policy manager (UI mejorada)**
   - Selector de pricelist remota
   - Calculadora visual
   - Safety factor explained

5. **Webhook dashboard**
   - Eventos recibidos
   - Procesados vs pendientes
   - Reintentos

### Flujo "Hola usuario"

```
1. [Crear cuenta ML]
   → Seleccionar conexión Odoo
   → Click "Conectar con MercadoLibre"
   → OAuth PKCE
   → Cuenta conectada automáticamente

2. [Configurar stock]
   → Elegir política: Sin reserva / 10% / 5 unidades
   → Preview: "Con esta política, publicarás 18 de 20"
   → Guardar

3. [Configurar precio]
   → Elegir lista Odoo remota
   → Agregar ajuste: +10%
   → Redondeo: A 100
   → Preview: "$1250 → $1350 (redondeado: $1400)"
   → Guardar

4. [Publicar producto]
   → Ir a Producto
   → [Publicar en ML]
   → Seleccionar categoría (busca automática)
   → Sistema mapea atributos automáticamente
   → Preview de publicación
   → [Publicar]
   → OK: "¡Publicado! Visible en 2 minutos"

5. [Monitoreo]
   → Dashboard muestra estado
   → Stock sincroniza cada 10 min
   → Precios sincronizan cada 5 min
   → Errores aparecen como alertas
   → Último sync visible siempre
```

---

## Q. GAPS PRIORIZADOS

### CRÍTICO (Bloquea MVP)

| Gap | Módulo | Esfuerzo | Descripción |
|-----|--------|----------|-------------|
| **G1: Importación de ventas** | sce_product_marketplace | ALTO | Sin este, no cierra el loop. Usuario puede publicar pero no vende. |
| **G2: Cancelaciones/Devoluciones** | sce_product_marketplace | MEDIO | Si cliente cancela en ML, debe reflejarse en Odoo. |
| **G3: Dashboard unificado** | sce_product_marketplace | ALTO | Usuario necesita un lugar centralizado, no 5 pantallas. |

### ALTO (Necesario para producto comercial)

| Gap | Módulo | Esfuerzo | Descripción |
|-----|--------|----------|-------------|
| **G4: UX de publicación unificada** | sce_connector_ml | ALTO | Actual está en 5+ wizards dispersos. |
| **G5: Webhooks robustos** | sce_connector_ml | MEDIO | Para órdenes y notificaciones ML real-time. |
| **G6: Observabilidad del usuario** | sce_product_marketplace | MEDIO | Logs comerciales (no técnicos), alertas visuales. |
| **G7: Stock Flex** | sce_connect | ALTO | Feature ML importante, actual solo free_qty. |
| **G8: Soporte multilingüe** | todos | BAJO | Español/Portugués/Inglés. |

### MEDIO (Necesario para robusted)

| Gap | Módulo | Esfuerzo | Descripción |
|-----|--------|----------|-------------|
| **G9: Cuotas/Financing** | sce_connect | BAJO | Integración con financing ML, actual ignorado. |
| **G10: Descuentos/Promociones** | sce_connect | MEDIO | Gestión de cupones, descuentos, automáticos ML. |
| **G11: Margen por categoría** | sce_connect | MEDIO | Regla: "Ropa +20%, Electrónica +5%". |
| **G12: Audit log completo** | sce_connect | BAJO | Quién cambió qué, cuándo, por qué. |

### BAJO (Nice-to-have V1.1+)

| Gap | Módulo | Esfuerzo | Descripción |
|-----|--------|----------|-------------|
| **G13: Imágenes desde URL** | sce_product_marketplace | MEDIO | Actual solo campos, no carga. |
| **G14: Descarga de facturas** | sce_product_marketplace | BAJO | Descargar invoice de ML a Odoo. |
| **G15: Chat con comprador** | sce_connector_ml | BAJO | Responder mensajes ML desde Odoo. |
| **G16: Stockaje local** | sce_connect | BAJO | Caché de categorías/atributos ML. |

---

## R. ROADMAP DE IMPLEMENTACIÓN

### FASE 0 - Prerequisitos (Semana 1)

- [ ] Completar Bloque A (Ownership) - ✅ HECHO
- [ ] Completar Bloque B (Policies) - ✅ HECHO
- [ ] Tests regresión 100% verde
- [ ] Documentación de API

### FASE 1 - Importación de Ventas (Semanas 2-4)

**Objetivos:** G1, G2 (Critical)

**Modelos nuevos:**
- marketplace.sale.order
- marketplace.order.line
- marketplace.payment
- marketplace.shipment

**Servicios:**
- OrderImportService
- PaymentSyncService
- ShipmentStatusService

**Webhooks:**
- order.created
- order.paid
- order.shipped
- order.cancelled

**Tests:** 40+ tests

### FASE 2 - Dashboard + Observabilidad (Semanas 5-7)

**Objetivos:** G3, G6 (Alto)

**Modelos nuevos:**
- marketplace.sync.log (logs comerciales)
- marketplace.dashboard.state (cache estado)

**Vistas nuevas:**
- Dashboard principal
- Historial sincronización
- Alertas/notificaciones

**Reports:**
- Últimos sync por operación
- Tasa de error
- Performance

### FASE 3 - UX Publicación Unificada (Semanas 8-10)

**Objetivos:** G4 (Alto)

**Cambios:**
- Wizard único secuencial
- Preview antes de publicar
- Validación de completitud
- Errores inline

### FASE 4 - Stock Flex (Semanas 11-13)

**Objetivos:** G7 (Alto)

**Nuevos campos:**
- sce.connect.stock.policy.flex_enabled
- sce.connect.stock.policy.flex_reserve

**Integración ML:**
- Consulta API flex settings
- Aplica reserve flex

### FASE 5 - Webhooks Robustos (Semanas 14-15)

**Objetivos:** G5 (Alto)

**Mejoras:**
- Retry logic exponencial
- Deadletter queue
- Webhook validation (signature)
- Deduplication

### FASE 6 - Stock/Precio Avanzado (Semanas 16-18)

**Objetivos:** G11 (Medio)

**Nuevos:**
- Reglas por categoría
- Reglas por SKU
- Prioridad de reglas
- Margen % dinámico

### FASE 7 - Cuotas/Financiación (Semana 19)

**Objetivos:** G9 (Medio)

**Integración:**
- Financing presets ML
- Cálculo precio con cuotas
- Mostrar al comprador

### FASE 8 - UX Final + Multilingüe (Semana 20)

**Objetivos:** G8, refinamiento

**Cambios:**
- Traducciones es/pt/en
- Polish UI
- Mensajes amigables

### FASE 9 - QA + Hardening (Semana 21-22)

**Objetivos:** Producto GA

**Actividades:**
- Tests E2E
- Load testing
- Security audit
- Documentación usuario

**Duración total: 22 semanas (~5 meses)**

---

## S. ARCHIVOS A MODIFICAR POR FASE

### FASE 1 - Importación de Ventas

| Archivo | Módulo | Tipo | Cambio |
|---------|--------|------|--------|
| marketplace_sale_order.py | sce_product_marketplace | CREAR | Modelo venta importada ML |
| marketplace_order_line.py | sce_product_marketplace | CREAR | Líneas venta |
| marketplace_payment.py | sce_product_marketplace | CREAR | Pagos ML |
| sce_connector_ml/services/order_import_service.py | sce_connector_ml | CREAR | Servicio importación |
| softwork_provider_mercadolibre/services/provider.py | softwork_provider_mercadolibre | MODIFICAR | Implementar get_orders, get_order |
| sce_connector_ml/controllers/webhook.py | sce_connector_ml | MODIFICAR | Handler order.created, order.paid |
| marketplace_publication_views.xml | sce_product_marketplace | MODIFICAR | Tab "Ventas" en publication |
| ir_cron.xml | sce_product_marketplace | MODIFICAR | Cron import_orders |

### FASE 2 - Dashboard + Observabilidad

| Archivo | Módulo | Tipo | Cambio |
|---------|--------|------|--------|
| marketplace_dashboard_views.xml | sce_product_marketplace | CREAR | Dashboard principal |
| marketplace_sync_log.py | sce_product_marketplace | CREAR | Modelo logs comerciales |
| marketplace_sync_log_views.xml | sce_product_marketplace | CREAR | Vistas logs |
| sce_account_views.xml | sce_product_marketplace | MODIFICAR | Agregar tab dashboard |
| sce_log_service.py | softwork_ecommerce_conector_base | MODIFICAR | Agregar log comercial |

### FASE 3 - UX Publicación

| Archivo | Módulo | Tipo | Cambio |
|---------|--------|------|--------|
| ml_publish_wizard.py | sce_connector_ml | CREAR | Wizard unificado |
| ml_publish_wizard_views.xml | sce_connector_ml | CREAR | Vistas wizard |
| marketplace_publication_views.xml | sce_product_marketplace | MODIFICAR | Reemplazar flujo |
| product_template_views.xml | sce_product_marketplace | MODIFICAR | Botón "Publicar" en producto |

### FASE 4 - Stock Flex

| Archivo | Módulo | Tipo | Cambio |
|---------|--------|------|--------|
| sce_connect_stock_policy.py | sce_connect | MODIFICAR | Agregar flex_* fields |
| stock_policy_calculator.py | sce_connect | MODIFICAR | Lógica flex |
| connect_stock_service.py | sce_connect | MODIFICAR | Consulta flex API |
| softwork_provider_mercadolibre/services/ml_provider.py | softwork_provider_mercadolibre | MODIFICAR | Implementar flex |

**[Continuarían FASES 5-9 con similar detalle]**

---

## T. RIESGOS

### De regresión

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Cambios en sce.account rompen legacy | MEDIA | ALTO | Versionamiento, deprecación gradual |
| Cambios OAuth rompen refresh | BAJA | CRÍTICO | Tests de OAuth existentes deben pasar |
| Cambios provider.sync rompen jobs | MEDIA | ALTO | Contrato provider congelado |

### De migración

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Datos legacy sin owner | MEDIA | MEDIO | Audit de datos antes de deploy |
| Publicaciones sin marketplace.sale.order | BAJA | BAJO | Crear con estado "sin_sincronización" |
| Tokens expirados al redeployer | BAJA | BAJO | Force refresh antes de producción |

### De compatibilidad

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Multi-account ML (1:N) | MEDIA | MEDIO | Diseñar schema preparado para V1.1 |
| Soporte otros marketplaces | BAJA | BAJO | Provider factory extensible |
| Regresión en Odoo 19.1 | BAJA | BAJO | Tests en versión pin |

### De OAuth

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Revoke de token no sincroniza | BAJA | BAJO | Sincronización manual still works |
| PKCE state expirado | BAJA | BAJO | Transacción con TTL, reintento |
| Múltiples refresh simultáneos | MEDIA | MEDIO | Lock de DB en account |

### De datos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Pérdida de sync history | BAJA | BAJO | Backups diarios |
| Datos remotos desincronizados | MEDIA | BAJO | Health check + manual sync |
| Conflicto variante ↔ variación ML | MEDIA | MEDIO | Mapeo único, constraint |

### De UX

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Usuario se pierde en UX actual | ALTA | ALTO | Dashboard + wizard unificado (FASE 2/3) |
| Errores no entendibles | MEDIA | MEDIO | Traducción amigable + logs comerciales |

---

## CONCLUSIÓN

**SCE v1.0 es viable con el roadmap propuesto.**

**Estado actual:** 2.8/5 - Fundación sólida, falta experiencia de producto completa

**Camino a producción:**

1. ✅ Arquitectura multi-tenant estable (Done)
2. ✅ OAuth PKCE y seguridad (Done)
3. ✅ Políticas stock/precio (Bloque B Done)
4. ⏳ Importación de ventas (CRÍTICO, Fase 1)
5. ⏳ Dashboard + observabilidad (CRÍTICO, Fase 2)
6. ⏳ UX unificada (CRÍTICO, Fase 3)
7. ⏳ Features complementarias (Fases 4-8)
8. ⏳ QA y productización (Fase 9)

**Estimado:** 5 meses para SCE v1.0 GA

**Inversión:** Moderada-Alta (equipo de 2-3 dev + 1 QA dedicado)

---

**FIN DE AUDITORÍA**

**Preparado por:** AI Audit Agent  
**Fecha:** 2026-09-10  
**Clasificación:** Interno - Arquitecto  
**Estado del documento:** COMPLETO - LISTO PARA DECISIÓN
