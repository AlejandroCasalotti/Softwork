#!/bin/bash

# SCE Connect - Setup y Validación Rápida
# Este script configura el entorno Odoo y ejecuta los tests de SCE Connect

set -e

WORKSPACE="/workspaces/Softwork"
VENV="$WORKSPACE/.venv"
ODOO_CONFIG="$HOME/.odoo/odoo.conf"
ODOO_PORT="${ODOO_PORT:-8069}"
ODOO_DB="${ODOO_DB:-sce_connect_test}"

echo "════════════════════════════════════════════════════════════════"
echo "SCE Connect - Setup y Validación de Fase 1"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Paso 1: Activar venv
echo "[1/6] Activando venv Python..."
source "$VENV/bin/activate"
echo "✓ Venv activado"
echo ""

# Paso 2: Verificar/Instalar Odoo
echo "[2/6] Verificando Odoo 19..."
if python -c "import odoo.tools" 2>/dev/null; then
    echo "✓ Odoo 19 ya está instalado"
else
    echo "→ Instalando Odoo 19 desde GitHub (esto puede tomar varios minutos)..."
    pip install --upgrade pip setuptools wheel -q
    pip install git+https://github.com/odoo/odoo.git@19.0 -q
    pip install cryptography requests -q
    echo "✓ Odoo 19 instalado"
fi
echo ""

# Paso 3: Generar clave maestra para secret storage
echo "[3/6] Configurando secret storage..."
if [ -z "$SCE_CONNECT_MASTER_KEY" ]; then
    export SCE_CONNECT_MASTER_KEY=$(python << 'EOF'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
EOF
)
fi
echo "✓ Master key: ${SCE_CONNECT_MASTER_KEY:0:30}..."
echo ""

# Paso 4: Crear estructura de directorio
echo "[4/6] Preparando configuración..."
mkdir -p "$HOME/.odoo"
mkdir -p /tmp/odoo_logs
echo "✓ Directorios creados"
echo ""

# Paso 5: Crear archivo de configuración
echo "[5/6] Configurando Odoo..."
cat > "$ODOO_CONFIG" << ODOO_CONF
[options]
addons_path = $WORKSPACE/marketplace_connector/addons
db_driver = sqlite
db_name = /tmp/$ODOO_DB.db
logfile = /tmp/odoo_logs/odoo.log
log_level = info
workers = 0
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_request = 8192
limit_time_cpu = 60
limit_time_real = 120
http_port = $ODOO_PORT
ODOO_CONF
echo "✓ Configuración guardada en $ODOO_CONFIG"
echo ""

# Paso 6: Información de ejecución
echo "[6/6] Preparación completada"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Próximos pasos: VALIDACIÓN FASE 1"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Lee: VALIDACION_FINAL_FASE1.md"
echo ""
echo "Resumen rápido:"
echo ""
echo "1. Instalar PostgreSQL:"
echo "   sudo apt-get install -y postgresql postgresql-contrib"
echo "   sudo service postgresql start"
echo ""
echo "2. Crear usuario y BD:"
echo "   sudo -u postgres psql << EOF"
echo "   CREATE USER odoo WITH PASSWORD 'odoo';"
echo "   ALTER USER odoo CREATEDB;"
echo "   CREATE DATABASE sce_connect_test OWNER odoo;"
echo "   EOF"
echo ""
echo "3. Inicializar Odoo con SCE Connect:"
echo "   cd $WORKSPACE"
echo "   source .venv/bin/activate"
echo "   export SCE_CONNECT_MASTER_KEY='$SCE_CONNECT_MASTER_KEY'"
echo "   python -m odoo server \\"
echo "     --config $ODOO_CONFIG \\"
echo "     --db_name sce_connect_test \\"
echo "     --init base,web,account,stock,sale,purchase,product \\"
echo "     --without-demo --stop-after-init"
echo ""
echo "4. Instalar SCE Connect:"
echo "   python -m odoo server \\"
echo "     --config $ODOO_CONFIG \\"
echo "     --db_name sce_connect_test \\"
echo "     -i softwork_ecommerce_conector_base,sce_connect \\"
echo "     --stop-after-init"
echo ""
echo "5. Iniciar servidor:"
echo "   python -m odoo server \\"
echo "     --config $ODOO_CONFIG \\"
echo "     --db_name sce_connect_test \\"
echo "     --dev xml"
echo "   # Accede a http://localhost:$ODOO_PORT"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Guardando configuración en ~/.bashrc..."
cat >> ~/.bashrc << 'BASHRC_ADD'

# SCE Connect environment
export SCE_CONNECT_MASTER_KEY='KEEP_YOUR_KEY'
BASHRC_ADD

echo "✓ Setup completado. Ejecuta una de las opciones anteriores."
