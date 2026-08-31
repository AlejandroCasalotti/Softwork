#!/usr/bin/env python
"""
SCE Connect Tests Runner - Versión aislada
Solo ejecuta tests de servicios puros (sin Odoo models)
"""

import sys
import os
import unittest
import importlib.util

WORKSPACE = "/workspaces/Softwork"
TESTS_DIR = f"{WORKSPACE}/marketplace_connector/addons/sce_connect/tests"
SERVICES_DIR = f"{WORKSPACE}/marketplace_connector/addons/sce_connect/services"

# Configurar environment
os.environ.setdefault("SCE_CONNECT_MASTER_KEY", 
    os.environ.get("SCE_CONNECT_MASTER_KEY", ""))

sys.path.insert(0, SERVICES_DIR)
sys.path.insert(0, TESTS_DIR)

def load_test_file(filepath, test_class_names=None):
    """Cargar módulo de test desde archivo"""
    spec = importlib.util.spec_from_file_location("test_module", filepath)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"✗ Error cargando {filepath}: {e}")
        return None

def main():
    print("=" * 70)
    print("SCE Connect - Tests de Servicios (Aislados)")
    print("=" * 70)
    print()
    
    suite = unittest.TestSuite()
    
    # Tests de servicios puros
    test_files = [
        ("test_secret_storage.py", ["SecretStorageTests"]),
        ("test_odoo_adapter.py", ["OdooAdapterTests"]),
        ("test_mercadolibre_transport.py", ["MercadoLibreTransportTests"]),
        ("test_connection_service.py", ["ConnectionServiceTests"]),
    ]
    
    print("Cargando tests...")
    for test_file, classes in test_files:
        filepath = os.path.join(TESTS_DIR, test_file)
        if not os.path.exists(filepath):
            print(f"✗ No encontrado: {filepath}")
            continue
        
        try:
            module = load_test_file(filepath, classes)
            if module:
                loader = unittest.TestLoader()
                for class_name in classes:
                    if hasattr(module, class_name):
                        test_class = getattr(module, class_name)
                        tests = loader.loadTestsFromTestCase(test_class)
                        suite.addTests(tests)
                        print(f"✓ {test_file} / {class_name}")
        except Exception as e:
            print(f"✗ Error en {test_file}: {e}")
    
    print()
    print("-" * 70)
    print()
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    print(f"Tests ejecutados: {result.testsRun}")
    print(f"Fallos: {len(result.failures)}")
    print(f"Errores: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✓ TODOS LOS TESTS PASARON")
        print("=" * 70)
        return 0
    else:
        print("✗ ALGUNOS TESTS FALLARON")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
