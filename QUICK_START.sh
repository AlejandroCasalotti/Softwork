#!/bin/bash
# SCE Connect - Quick Start
# Copia-pega estos comandos en tu terminal

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "SCE Connect - Quick Start Validación Fase 1"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# 1. Activar venv
echo "[1/5] Activando venv..."
cd /workspaces/Softwork
source .venv/bin/activate
echo "✓ Venv activado"
echo ""

# 2. Master key
echo "[2/5] Generando master key..."
export SCE_CONNECT_MASTER_KEY=$(python << 'EOF'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
EOF
)
echo "✓ Master key: ${SCE_CONNECT_MASTER_KEY:0:30}..."
echo ""

# 3. Verificar Odoo
echo "[3/5] Verificando Odoo..."
python -c "import odoo.tools; print('✓ Odoo 19 disponible')"
echo ""

# 4. Verificar estructura
echo "[4/5] Verificando estructura de SCE Connect..."
python -m compileall marketplace_connector/addons/sce_connect -q
echo "✓ Sin errores de sintaxis"
echo ""

# 5. Resumen
echo "[5/5] Status"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ ENTORNO LISTO"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "AHORA:"
echo ""
echo "1. Lee la guía de validación:"
echo "   cat VALIDACION_FINAL_FASE1.md"
echo ""
echo "2. Instala PostgreSQL (si lo necesitas):"
echo "   sudo apt-get install -y postgresql postgresql-contrib"
echo "   sudo service postgresql start"
echo ""
echo "3. Crea usuario y BD:"
echo "   sudo -u postgres psql << EOF"
echo "   CREATE USER odoo WITH PASSWORD 'odoo';"
echo "   ALTER USER odoo CREATEDB;"
echo "   CREATE DATABASE sce_connect_test OWNER odoo;"
echo "   EOF"
echo ""
echo "4. Inicializa Odoo con SCE Connect:"
echo "   source .venv/bin/activate"
echo "   export SCE_CONNECT_MASTER_KEY='$SCE_CONNECT_MASTER_KEY'"
echo "   python -m odoo server \\"
echo "     --config ~/.odoo/odoo.conf \\"
echo "     --db_name sce_connect_test \\"
echo "     --init base,web,account,stock,sale,purchase,product \\"
echo "     --without-demo --stop-after-init"
echo ""
echo "5. Instala SCE Connect:"
echo "   python -m odoo server \\"
echo "     --config ~/.odoo/odoo.conf \\"
echo "     --db_name sce_connect_test \\"
echo "     -i softwork_ecommerce_conector_base,sce_connect \\"
echo "     --stop-after-init"
echo ""
echo "6. Inicia servidor:"
echo "   python -m odoo server \\"
echo "     --config ~/.odoo/odoo.conf \\"
echo "     --db_name sce_connect_test \\"
echo "     --dev xml"
echo "   # Luego: http://localhost:8069"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Master Key guardada (guardar de forma segura):"
echo "$SCE_CONNECT_MASTER_KEY"
echo ""
