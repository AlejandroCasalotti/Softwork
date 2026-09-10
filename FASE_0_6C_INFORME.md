# Fase 0.6-C — Mercado Libre nativo de SCE sin dependencia de SCE Connect

## Objetivo

Implementar y validar la capa comercial nativa de Mercado Libre en SCE, sin que el flujo principal dependa de `sce_connect`. La compatibilidad con el módulo legacy debe seguir existiendo, pero no como fuente de verdad ni como dependencia forzada del corazón comercial de SCE.

## Principio arquitectónico

- `SCE Connect` queda como capa opcional de compatibilidad.
- `SCE core` define y gestiona el flujo nativo de Mercado Libre.
- La autenticación usa OAuth con PKCE `S256`, `state` único, intercambio de código y renovación de token.
- Los secreto y tokens se persisten en un servicio de credenciales centralizado, no en campos legacy del módulo Connect.

## Implementación nativa ya presente en el repo

### 1) Cuenta comercial ML sin dependencia de Connect

El modelo principal ya expone acciones nativas para empezar la conexión, refrescar tokens y desconectar.

- [marketplace_connector/addons/sce_connector_ml/models/sce_account.py](marketplace_connector/addons/sce_connector_ml/models/sce_account.py)

Funciones clave:
- `action_open_oauth_url()`
- `action_start_onboarding_connection()`
- `action_refresh_token()`
- `action_disconnect_mercadolibre()`

### 2) OAuth del proveedor nativo ML

El servicio principal del flujo OAuth ya está implementado y sigue la política de PKCE y validación de transacción:

- [marketplace_connector/addons/sce_connector_ml/services/mercadolibre_oauth_service.py](marketplace_connector/addons/sce_connector_ml/services/mercadolibre_oauth_service.py)

Funciones clave:
- `start()`
- `complete()`
- `_pkce_pair()`

### 3) Gestión de tokens y refresh rotatorio

La rotación y persistencia de tokens se resuelven en el servicio de tokens nativo:

- [marketplace_connector/addons/sce_connector_ml/services/mercadolibre_token_service.py](marketplace_connector/addons/sce_connector_ml/services/mercadolibre_token_service.py)

Funciones clave:
- `store_tokens()`
- `get_access_token()`
- `refresh()`
- `disconnect()`

### 4) Registro seguro de transacciones OAuth

La transacción de autorización se guarda con hash de `state` y single-use semantics:

- [marketplace_connector/addons/sce_connector_ml/models/sce_oauth_transaction.py](marketplace_connector/addons/sce_connector_ml/models/sce_oauth_transaction.py)

Funciones clave:
- `hash_state()`
- `consume()`

### 5) Secretos cifrados en el core

Los tokens y verifiers PKCE no se almacenan a texto plano. Se encapsulan en el servicio de secretos del core:

- [marketplace_connector/addons/sce_connector_ml/models/sce_credential_secret.py](marketplace_connector/addons/sce_connector_ml/models/sce_credential_secret.py)
- [marketplace_connector/addons/sce_connector_ml/services/core_secret_service.py](marketplace_connector/addons/sce_connector_ml/services/core_secret_service.py)

### 6) Identidad ML del vendedor

El modelo `sce.mercadolibre.account` es la identidad comercial vinculada al account de SCE:

- [marketplace_connector/addons/sce_connector_ml/models/sce_mercadolibre_account.py](marketplace_connector/addons/sce_connector_ml/models/sce_mercadolibre_account.py)

Campos relevantes:
- `seller_user_id`
- `seller_nickname`
- `scopes`
- `expires_at`
- `access_token_secret_id`
- `refresh_token_secret_id`

## Qué no se tocó como parte de la fase 0.6-C

- No se eliminó ni mutiló el módulo `sce_connect`.
- No se hicieron migraciones destructivas.
- No se borraron tablas ni compatibilidad legacy.
- El módulo Connect queda como extensión opcional, no como definidor del core.

## Puntos de compatibilidad que siguen intactos

Las capas de compatibilidad legacy siguen presentes en:

- [marketplace_connector/addons/softwork_ecommerce_conector_base/services/provider_factory.py](marketplace_connector/addons/softwork_ecommerce_conector_base/services/provider_factory.py)
- [marketplace_connector/addons/softwork_ecommerce_conector_base/services/providers/ml_provider.py](marketplace_connector/addons/softwork_ecommerce_conector_base/services/providers/ml_provider.py)
- [marketplace_connector/addons/sce_connect/models/sce_account.py](marketplace_connector/addons/sce_connect/models/sce_account.py)

Esto garantiza que no haya ruptura de instalaciones previas, pero la fuente de verdad del flujo nativo ML queda en `sce_connector_ml`.

## Validación técnica realizada

Se ejecutó esta validación:

```bash
cd /workspaces/Softwork && python -m compileall marketplace_connector/addons/sce_connector_ml marketplace_connector/addons/softwork_ecommerce_conector_base
```

Resultado: compilación exitosa, sin errores Python en los módulos verificados.

## Estado real

La fase 0.6-C queda en una condición técnica coherente y verificable en este repositorio:

- flujo nativo ML implementado,
- separación del core y Connect mantenida,
- compatibilidad legacy preservada,
- compilación validada,
- sin migración destructiva.

## Limitación del entorno actual

Este workspace no incluye un runtime Odoo real con base de datos operativa para hacer una prueba end-to-end con callback OAuth real de Mercado Libre. Por tanto, la validación realizada aquí es de sintaxis / estructura del flujo y de coherencia arquitectónica, no una autenticación real de producción.

## Conclusión

El repositorio ya está orientado a la arquitectura pedida por la fase 0.6-C: el corazón comercial de SCE puede conectarse a Mercado Libre de forma nativa y sin depender de `sce_connect`, manteniendo a Connect como capa opcional de compatibilidad.
