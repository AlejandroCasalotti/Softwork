#!/usr/bin/env python
"""
SCE Connect Tests Runner
Ejecuta los tests de SCE Connect de forma aislada sin requerer BD Odoo
"""

import sys
import os
import unittest

# Agregar el workspace al path
WORKSPACE = "/workspaces/Softwork"
sys.path.insert(0, WORKSPACE)
sys.path.insert(0, f"{WORKSPACE}/marketplace_connector/addons")

# Configurar environment
os.environ.setdefault("SCE_CONNECT_MASTER_KEY", os.environ.get("SCE_CONNECT_MASTER_KEY", ""))

def run_pure_python_tests():
    """Ejecuta tests que no requieren Odoo runtime"""
    
    print("=" * 70)
    print("SCE Connect - Tests de Servicios (Sin BD Odoo)")
    print("=" * 70)
    print()
    
    # Importar módulos de test puros (sin dependencia Odoo)
    test_modules = [
        "sce_connect.tests.test_secret_storage",
        "sce_connect.tests.test_odoo_adapter", 
        "sce_connect.tests.test_mercadolibre_transport",
    ]
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            module_tests = loader.loadTestsFromModule(module)
            suite.addTests(module_tests)
            print(f"✓ Módulo {module_name} cargado")
        except ImportError as e:
            print(f"✗ No se pudo cargar {module_name}: {e}")
            continue
    
    print()
    print("-" * 70)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("✓ TODOS LOS TESTS PASARON")
        return 0
    else:
        print(f"✗ TESTS FALLIDOS: {len(result.failures)} fallos, {len(result.errors)} errores")
        return 1

if __name__ == "__main__":
    sys.exit(run_pure_python_tests())
