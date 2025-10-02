#!/usr/bin/env python3
"""
Script de validation finale des tests pour s'assurer que le pipeline CI/CD passera.
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Execute a command and return the result."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minutes timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def main():
    """Main validation function."""
    print("🧪 Validation finale des tests YouTube ELT Pipeline")
    print("=" * 60)
    
    # Get project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if tests directory exists
    if not (project_root / "tests").exists():
        print("❌ Répertoire 'tests' non trouvé!")
        return False
    
    # Count test files
    test_files = list((project_root / "tests").glob("test_*.py"))
    print(f"📁 Fichiers de test trouvés: {len(test_files)}")
    for test_file in test_files:
        print(f"   - {test_file.name}")
    
    print("\n🔍 Exécution des tests...")
    
    # Run pytest with the same parameters as CI/CD
    cmd = "python -m pytest -q --maxfail=1 --disable-warnings --cov=plugins --cov-report=xml tests/"
    
    success, stdout, stderr = run_command(cmd)
    
    print("\n📊 Résultats:")
    print("-" * 40)
    
    if success:
        print("✅ TOUS LES TESTS PASSENT!")
        print("\n📈 Sortie des tests:")
        print(stdout)
        
        # Check if coverage file was generated
        if (project_root / "coverage.xml").exists():
            print("✅ Rapport de couverture généré: coverage.xml")
        else:
            print("⚠️  Rapport de couverture non trouvé")
        
        print("\n🎉 Le pipeline CI/CD devrait passer avec succès!")
        return True
    else:
        print("❌ ÉCHEC DES TESTS!")
        print("\n📋 Sortie d'erreur:")
        print(stderr)
        print("\n📋 Sortie standard:")
        print(stdout)
        
        print("\n🔧 Actions recommandées:")
        print("1. Vérifiez les erreurs ci-dessus")
        print("2. Corrigez les tests qui échouent")
        print("3. Relancez ce script de validation")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
