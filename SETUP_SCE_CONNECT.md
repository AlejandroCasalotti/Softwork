# Setup y Validación de SCE Connect Fase 1

## Requisitos previos

- Python 3.12 (disponible en el dev container)
- PostgreSQL 12+ (recomendado) o SQLite para testing local  
- Git (ya configurado)
- Odoo 19 (se instalará desde repositorio oficial)

## Paso 1: Instalar Odoo 19 desde repositorio oficial

```bash
cd /workspaces/Softwork

# Activar venv
source .venv/bin/activate

# Instalar Odoo 19 desde GitHub + dependencias
pip install --upgrade pip setuptools wheel
pip install git+https://github.com/odoo/odoo.git@19.0
pip install cryptography requests

# Verificar instalación
python -c "import odoo.tools; print('✓ Odoo 19 instalado')"
python -c "from cryptography.fernet import Fernet; print('✓ Cryptography instalada')"
```

## Paso 2: Configurar PostgreSQL (Recomendado para desarrollo)

### Opción A: PostgreSQL local en el dev container

```bash
# Instalar PostgreSQL
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib

# Iniciar el servicio
sudo service postgresql start

# Crear usuario y base de datos para Odoo
sudo -u postgres psql << EOF
CREATE USER odoo WITH PASSWORD 'odoo';
ALTER USER odoo CREATEDB;
CREATE DATABASE sce_connect_test OWNER odoo;
EOF

# Verificar conexión
psql -U odoo -d sce_connect_test -c "SELECT 1;"
```

### Opción B: SQLite para testing rápido (sin PostgreSQL)

SQLite está disponible por defecto en Python. Usa `--db_driver=sqlite` en los comandos.

## Paso 3: Preparar la estructura de Odoo

```bash
cd /workspaces/Softwork

# Crear estructura de config
mkdir -p ~/.odoo

# Crear archivo de configuración odoo.conf
cat > ~/.odoo/odoo.conf << 'EOF'
[options]
addons_path = /workspaces/Softwork/marketplace_connector/addons
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
db_name = sce_connect_test
logfile = /tmp/odoo.log
log_level = info
workers = 0
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_request = 8192
limit_time_cpu = 60
limit_time_real = 120
EOF
```

## Paso 4: Crear/Inicializar la base de datos

```bash
cd /workspaces/Softwork

# Opción A: Con PostgreSQL
python -m odoo.bin.odoo -c ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  --init base,web,account,stock,sale,purchase,product \
  --without-demo \
  --stop-after-init

# Opción B: Con SQLite
python -m odoo.bin.odoo \
  --db_driver sqlite \
  --db_name /tmp/sce_connect_test.db \
  --init base,web,account,stock,sale,purchase,product \
  --without-demo \
  --stop-after-init
```

## Paso 5: Instalar el addon sce_connect

```bash
cd /workspaces/Softwork

# Con PostgreSQL
python -m odoo.bin.odoo -c ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  -i softwork_ecommerce_conector_base,sce_connect \
  --without-demo \
  --stop-after-init

# Con SQLite
python -m odoo.bin.odoo \
  --db_driver sqlite \
  --db_name /tmp/sce_connect_test.db \
  -i softwork_ecommerce_conector_base,sce_connect \
  --without-demo \
  --stop-after-init
```

## Paso 6: Ejecutar los tests de SCE Connect

### Opción A: Tests desde Odoo (completo)

```bash
cd /workspaces/Softwork

# Con PostgreSQL
python -m odoo.bin.odoo -c ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  --test-enable \
  -u sce_connect \
  --stop-after-init

# Con SQLite
python -m odoo.bin.odoo \
  --db_driver sqlite \
  --db_name /tmp/sce_connect_test.db \
  --test-enable \
  -u sce_connect \
  --stop-after-init
```

### Opción B: Tests unitarios de servicios (sin Odoo runtime)

```bash
cd /workspaces/Softwork

# Ejecutar tests de servicios puros
python -m unittest \
  odoo.addons.sce_connect.tests.test_secret_storage \
  odoo.addons.sce_connect.tests.test_odoo_adapter \
  odoo.addons.sce_connect.tests.test_mercadolibre_transport \
  -v
```

### Opción C: Tests de seguridad y modelos (requiere Odoo + BD)

```bash
cd /workspaces/Softwork

# Configurar master key para secret storage
export SCE_CONNECT_MASTER_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Con PostgreSQL
python -m odoo.bin.odoo -c ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  --test-enable \
  -u sce_connect \
  --test-tags="sce_connect" \
  --stop-after-init 2>&1 | tee /tmp/sce_connect_tests.log

# Ver resultados
grep -E "test_|ERROR|FAIL|OK" /tmp/sce_connect_tests.log
```

## Paso 7: Validaciones manuales

### 7.1 Verificar que los modelos fueron creados

```bash
cd /workspaces/Softwork

python << 'EOF'
import os
os.environ.setdefault("ODOO_VERSION", "19")
os.environ.setdefault("DB_NAME", "sce_connect_test")

from odoo import api, SUPERUSER_ID
from odoo.tools import config

config.set_option("db_name", "sce_connect_test")
config.set_option("db_user", "odoo")
config.set_option("db_password", "odoo")

with api.Environment.manage():
    env = api.Environment(None, SUPERUSER_ID, {})
    
    # Verificar modelos
    models_to_check = [
        "sce.tenant",
        "sce.external.connection",
        "sce.secret",
        "sce.mercadolibre.account",
    ]
    
    for model_name in models_to_check:
        try:
            env[model_name]
            print(f"✓ {model_name} instalado correctamente")
        except KeyError:
            print(f"✗ {model_name} NO está instalado")
EOF
```

### 7.2 Crear un tenant de prueba

```bash
cd /workspaces/Softwork

python << 'EOF'
import os
from odoo import api, SUPERUSER_ID

os.environ.setdefault("DB_NAME", "sce_connect_test")

with api.Environment.manage():
    from odoo.tools import config
    config.set_option("db_name", "sce_connect_test")
    config.set_option("db_user", "odoo")
    config.set_option("db_password", "odoo")
    
    env = api.Environment(None, SUPERUSER_ID, {})
    
    # Crear tenant
    tenant = env["sce.tenant"].create({
        "name": "Test Tenant",
        "code": "test-tenant",
    })
    print(f"✓ Tenant creado: {tenant.id} ({tenant.code})")
    
    # Crear secreto
    from odoo.addons.sce_connect.services.secret_storage import SecretStorage
    storage = SecretStorage.from_environment()
    
    secret = env["sce.secret"].create({
        "name": "Test API Key",
        "tenant_id": tenant.id,
        "secret_type": "odoo_api_key",
    })
    secret.with_context(sce_backend_secret_access=True).set_value("test-api-key-value")
    print(f"✓ Secreto creado: {secret.id}")
    
    # Crear conexión externa
    connection = env["sce.external.connection"].create({
        "name": "Test Odoo Connection",
        "tenant_id": tenant.id,
        "url": "https://demo.odoo.com",
        "database": "demo_db",
        "user": "test@example.com",
        "secret_id": secret.id,
    })
    print(f"✓ Conexión creada: {connection.id}")
EOF
```

### 7.3 Probar conexión a Odoo externo

```bash
cd /workspaces/Softwork

python << 'EOF'
import os
from odoo import api, SUPERUSER_ID

os.environ.setdefault("DB_NAME", "sce_connect_test")

with api.Environment.manage():
    from odoo.tools import config
    config.set_option("db_name", "sce_connect_test")
    config.set_option("db_user", "odoo")
    config.set_option("db_password", "odoo")
    
    env = api.Environment(None, SUPERUSER_ID, {})
    
    # Obtener la conexión
    connection = env["sce.external.connection"].search([], limit=1)
    
    if connection:
        # Intentar conexión (esto fallará si el Odoo remoto no existe)
        try:
            result = connection.action_test_connection()
            print(f"✓ Test de conexión ejecutado: {result}")
        except Exception as e:
            print(f"⚠ Test falló (esperado si el Odoo remoto no existe): {e}")
EOF
```

## Paso 8: Iniciar servidor Odoo para desarrollo interactivo

```bash
cd /workspaces/Softwork

# Con PostgreSQL
python -m odoo.bin.odoo -c ~/.odoo/odoo.conf \
  --db_name sce_connect_test \
  --dev xml \
  --log-level info

# Con SQLite
python -m odoo.bin.odoo \
  --db_driver sqlite \
  --db_name /tmp/sce_connect_test.db \
  --dev xml \
  --log-level info
```

Luego accede a: `http://localhost:8069`

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'odoo'`
Solución: Asegúrate de activar el venv y de instalar Odoo:
```bash
source /workspaces/Softwork/.venv/bin/activate
pip install odoo==19.0
```

### Error: `FATAL: role "odoo" does not exist`
Solución: Crear el usuario de PostgreSQL:
```bash
sudo -u postgres psql << EOF
CREATE USER odoo WITH PASSWORD 'odoo';
ALTER USER odoo CREATEDB;
EOF
```

### Error: `SCE_CONNECT_MASTER_KEY` faltante
Solución: Generar e instalar la clave maestra:
```bash
export SCE_CONNECT_MASTER_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "SCE_CONNECT_MASTER_KEY=$SCE_CONNECT_MASTER_KEY" >> ~/.bashrc
```

### Error: Puerto 8069 en uso
Solución: Cambiar puerto:
```bash
python -m odoo.bin.odoo \
  -c ~/.odoo/odoo.conf \
  --http-port 8070
```

## Resumen de comandos rápidos

```bash
# Setup completo en un paso
cd /workspaces/Softwork && \
source .venv/bin/activate && \
pip install odoo==19.0 cryptography requests && \
export SCE_CONNECT_MASTER_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") && \
python -m odoo.bin.odoo --help | head -20

# Ejecutar tests
python -m unittest \
  odoo.addons.sce_connect.tests.test_secret_storage \
  odoo.addons.sce_connect.tests.test_odoo_adapter \
  -v

# Iniciar servidor de desarrollo
python -m odoo.bin.odoo -c ~/.odoo/odoo.conf --db_name sce_connect_test --dev xml
```
