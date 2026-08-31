#!/bin/bash

# SCE Connect - Inicializar BD e Instalar en Odoo
# Este script configura Odoo completamente y ejecuta los tests desde dentro

set -e

WORKSPACE="/workspaces/Softwork"
VENV="$WORKSPACE/.venv"
ODOO_CONFIG="$HOME/.odoo/odoo.conf"
ODOO_DB="sce_connect_test"
MASTER_KEY="${SCE_CONNECT_MASTER_KEY:-}"

if [ -z "$MASTER_KEY" ]; then
    MASTER_KEY=$(python3 << 'EOF'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
EOF
)
fi

echo "════════════════════════════════════════════════════════════════"
echo "SCE Connect - Inicializar BD Odoo"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Base de datos: $ODOO_DB"
echo "Config: $ODOO_CONFIG"
echo "Master Key: ${MASTER_KEY:0:30}..."
echo ""

# Activar venv
source "$VENV/bin/activate"

# Paso 1: Crear base de datos
echo "[1/3] Creando base de datos $ODOO_DB..."
python -m odoo db create --template=base "$ODOO_DB" 2>&1 | tail -5

echo ""
echo "[2/3] Instalando módulos base y SCE Connect..."
export SCE_CONNECT_MASTER_KEY="$MASTER_KEY"
python -m odoo -c "$ODOO_CONFIG" \
    server \
    --db_name "$ODOO_DB" \
    --init base,web,account,stock,sale,purchase,product,softwork_ecommerce_conector_base,sce_connect \
    --without-demo \
    --stop-after-init \
    2>&1 | tail -20

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✓ Instalación completada"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Base de datos SQLite: /tmp/$ODOO_DB.db"
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Ejecutar tests dentro de Odoo:"
echo "   export SCE_CONNECT_MASTER_KEY='$MASTER_KEY'"
echo "   python -m odoo -c $ODOO_CONFIG \\"
echo "     server --db_name $ODOO_DB \\"
echo "     --test-enable -u sce_connect \\"
echo "     --stop-after-init"
echo ""
echo "2. Iniciar servidor web:"
echo "   export SCE_CONNECT_MASTER_KEY='$MASTER_KEY'"
echo "   python -m odoo -c $ODOO_CONFIG \\"
echo "     server --db_name $ODOO_DB \\"
echo "     --dev xml"
echo "   Accede a http://localhost:8069"
echo ""
