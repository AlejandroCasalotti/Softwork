# Secuencia Final: Validar SCE Connect Fase 1 en Odoo

## Estado actual

✅ Odoo 19 instalado en `.venv`  
✅ Dependencias (cryptography, requests) disponibles  
✅ Master key generada para secret storage  
✅ Configuración de Odoo creada en `~/.odoo/odoo.conf`

## Requisito: PostgreSQL

**SCE Connect y Odoo 19 requieren PostgreSQL** (SQLite no es soportado para producción).

### Instalar PostgreSQL en el dev container

```bash
# Instalar PostgreSQL
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib postgresql-client

# Iniciar el servicio
sudo service postgresql start

# Crear usuario y base de datos
sudo -u postgres psql << EOF
CREATE USER odoo WITH PASSWORD 'odoo';
ALTER USER odoo CREATEDB;
CREATE DATABASE sce_connect_test OWNER odoo;
\q
EOF

# Verificar conexión
psql -h localhost -U odoo -d sce_connect_test -c "SELECT 1;"
```

## Secuencia de Validación (Con PostgreSQL)

### Paso 1: Activar venv y configurar variables

```bash
cd /workspaces/Softwork
source .venv/bin/activate

# Generar y exportar master key
export SCE_CONNECT_MASTER_KEY=$(python << 'EOF'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
EOF
)

echo "Master Key: $SCE_CONNECT_MASTER_KEY"
```

### Paso 2: Crear archivo de configuración Odoo para PostgreSQL

```bash
cat > ~/.odoo/odoo.conf << 'EOF'
[options]
addons_path = /workspaces/Softwork/marketplace_connector/addons
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
logfile = /tmp/odoo.log
log_level = info
workers = 0
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_request = 8192
limit_time_cpu = 60
limit_time_real = 120
http_port = 8069
EOF
```

### Paso 3: Inicializar base de datos Odoo

```bash
cd /workspaces/Softwork
source .venv/bin/activate
export SCE_CONNECT_MASTER_KEY='<tu_master_key>'

# Esto crea la BD e instala módulos base
python -m odoo server \
  --config ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  --init base,web,account,stock,sale,purchase,product \
  --without-demo \
  --stop-after-init
```

**Esperado:**
- La BD se crea automáticamente
- Los módulos base se instalan
- Tarda 5-10 minutos

### Paso 4: Instalar módulos SCE Connect

```bash
cd /workspaces/Softwork
source .venv/bin/activate
export SCE_CONNECT_MASTER_KEY='<tu_master_key>'

# Instalar los addons
python -m odoo server \
  --config ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  -i softwork_ecommerce_conector_base,sce_connect \
  --stop-after-init
```

**Esperado:**
- Los módulos se instalan correctamente
- Los modelos SCE Connect (sce.tenant, sce.secret, etc.) se crean

### Paso 5: Ejecutar tests desde Odoo

```bash
cd /workspaces/Softwork
source .venv/bin/activate
export SCE_CONNECT_MASTER_KEY='<tu_master_key>'

# Ejecutar tests de SCE Connect
python -m odoo server \
  --config ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  --test-enable \
  -u sce_connect \
  --stop-after-init 2>&1 | tee /tmp/tests.log

# Ver resumen de tests
grep -E "test|PASS|FAIL|ERROR" /tmp/tests.log | tail -50
```

**Esperado:**
- Tests de seguridad pasan (tenant isolation, record rules)
- Tests de OAuth pasan (state creation, validation)
- Tests de conexión pasan (error classification)

### Paso 6: Iniciar servidor Odoo para desarrollo

```bash
cd /workspaces/Softwork
source .venv/bin/activate
export SCE_CONNECT_MASTER_KEY='<tu_master_key>'

# Iniciar en modo desarrollo
python -m odoo server \
  --config ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  --dev xml
```

**Accede a:** http://localhost:8069

**Credenciales de prueba:**
- Usuario: `admin`
- Contraseña: `admin`

## Validaciones Manuales desde Odoo Web

Una vez en la interfaz web:

### 1. Verificar modelos SCE Connect

Menú → SCE Connect → Tenants

Deberías ver:
- Opción para crear tenant
- Campos: name, code, user_ids, company_id
- Record rules de seguridad funcionando

### 2. Crear tenant de prueba

1. Clic en "Create"
2. Nombre: "Test Tenant"
3. Código: "test-tenant"
4. Usuarios: Agregar usuario admin
5. Guardar

### 3. Crear secreto

Menú → SCE Connect → Secrets

1. Crear secreto nuevo
2. Nombre: "Test API Key"
3. Tenant: Test Tenant
4. Tipo: Odoo API Key
5. Clic en "Set Secret" (acción)
6. Ingresar valor: "test-api-key-12345"

**Verificar:**
- El secreto se cifra correctamente
- No aparece desencriptado en vistas
- Solo admin puede verlo

### 4. Crear conexión externa

Menú → SCE Connect → External Connections

1. Crear conexión
2. Nombre: "Demo Odoo"
3. Tenant: Test Tenant
4. URL: https://demo.odoo.com
5. Database: demo_db
6. User: admin@example.com
7. Secret: Test API Key
8. Clic en "Test Connection"

**Esperado:**
- Fallará (demo.odoo.com no existe) con error de red clasificado
- O si configuras una URL real, se conectará

### 5. Verificar seguridad multi-tenant

Crear otro usuario (no admin):

1. Menú → Configuración → Usuarios
2. Crear usuario "user@test.com"
3. Agregarle grupo "SCE Connect / User"

Luego con ese usuario:
- No debería ver datos del Tenant A si está en Tenant B
- Record rules deberían bloquear acceso cruzado

## Estructura de carpetas creadas

```
~/.odoo/
  └── odoo.conf          # Configuración Odoo

/tmp/
  ├── odoo.log           # Logs de Odoo
  ├── sce_connect_test.db  # BD SQLite (si usas SQLite, no recomendado)

/workspaces/Softwork/
  ├── SETUP_SCE_CONNECT.md   # Esta documentación
  ├── setup_sce_connect.sh   # Script de setup
  ├── init_odoo.sh           # Script de inicialización
  ├── run_tests.py           # Runner de tests
  ├── .venv/                 # Virtual environment
  └── marketplace_connector/addons/sce_connect/
      ├── models/            # Modelos Odoo (tenant, secret, conexión, etc.)
      ├── services/          # Servicios puros (adapters, OAuth, crypto)
      ├── controllers/       # Controllers (OAuth callbacks)
      ├── tests/             # Tests unitarios
      └── security/          # Record rules y acceso
```

## Troubleshooting

### Error: `No module named 'freezegun'`
```bash
pip install freezegun
```

### Error: `FATAL: role "odoo" does not exist`
```bash
sudo -u postgres psql << EOF
CREATE USER odoo WITH PASSWORD 'odoo';
ALTER USER odoo CREATEDB;
EOF
```

### Error: `Connection refused` (BD PostgreSQL)
```bash
# Verificar que PostgreSQL está en marcha
sudo service postgresql status

# O reiniciar
sudo service postgresql restart
```

### Error: Secreto no se guarda
Asegúrate de que SCE_CONNECT_MASTER_KEY está definida:
```bash
echo $SCE_CONNECT_MASTER_KEY
# Si está vacío, genera una nueva:
export SCE_CONNECT_MASTER_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### Error: Puerto 8069 en uso
```bash
# Cambiar puerto en odoo.conf:
http_port = 8070

# O liberar el puerto:
lsof -i :8069
kill -9 <PID>
```

## Resumen de Fase 1 Validada

Con esta secuencia habrás validado que **SCE Connect Fase 1** está funcionando:

✅ **Modelos:**
- `sce.tenant` - Multi-tenancy
- `sce.secret` - Almacenamiento cifrado de credenciales
- `sce.external.connection` - Conexiones a Odoo remoto
- `sce.mercadolibre.account` - Cuentas MercadoLibre
- `sce.oauth.transaction` - Estados OAuth

✅ **Servicios:**
- `SecretStorage` - Cifrado/descifrado con Fernet
- `BaseOdooAdapter` / `Odoo19Json2Adapter` - Conexión JSON-2 a Odoo remoto
- `MercadoLibreOAuthService` - OAuth PKCE con MercadoLibre
- `OAuthStateService` - Estados seguros, vinculados a tenant/usuario
- `ConnectionService` - Test y clasificación de errores

✅ **Seguridad:**
- Multi-tenancy enforcement (record rules)
- Secret storage sin exposición en logs
- SSRF protection en URLs remotas
- HTTPS obligatorio en producción
- Acceso controlado (solo grupo SCE Connect Admin ve secretos)

✅ **Tests:**
- Cifrado/descifrado de secretos
- Validación de URLs (HTTPS, no privadas)
- Clasificación de errores (auth, permisos, red, config)
- Aislamiento de tenant/usuario en OAuth

## Próximos pasos: Fase 2

Con Fase 1 validada, los siguientes pasos son:

1. **Refresh de tokens MercadoLibre** con locking y rotación
2. **Discovery de metadata** en Odoo remoto
3. **Mapeos configurables** entre sistemas
4. **Sincronización de productos** (lectura desde Odoo externo)
5. **Pricing engine** (cálculo de precios para marketplace)
6. **Publicaciones** (integración con conector ML actual)
7. **Órdenes** (importación desde MercadoLibre)
8. **Webhooks** (validación, deduplicación, rate limiting)

Cada fase mantiene compatibilidad con el legacy y puede desplegarse de forma incremental.
