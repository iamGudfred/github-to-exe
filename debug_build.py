#!/usr/bin/env python3
"""
Debug script to test build pipeline step by step
"""
import sys
from pathlib import Path
import tempfile

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_step_by_step():
    repo_url = "https://github.com/iamGudfred/test_simple_repo"

    print("=== Testing Build Pipeline Step by Step ===\n")

    # Test 1: Import modules
    print("1. Testing imports...")
    try:
        from build_manager import BuildManager, check_dependencies
        print("✅ BuildManager imported successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

    # Test 2: Check PyInstaller
    print("\n2. Testing PyInstaller...")
    if check_dependencies():
        print("✅ PyInstaller is available")
    else:
        print("❌ PyInstaller not found")
        print("Run: pip install pyinstaller")
        return False

    # Test 3: Test repository analysis
    print("\n3. Testing repository analysis...")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            build_mgr = BuildManager()
            analysis = build_mgr.analyze_repository(repo_url, temp_dir)
            print(f"✅ Analysis successful: {analysis}")

            if not analysis.get('can_build', False):
                print(f"❌ Analysis says cannot build: {analysis.get('issues', [])}")
                return False
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

    # Test 4: Test actual build
    print("\n4. Testing actual build...")
    try:
        build_data = {'url': repo_url}
        build_mgr = BuildManager()
        result = build_mgr.build_executable(build_data)
        print(f"Build result: {result}")

        if result.get('success'):
            print("✅ Build completed successfully!")
            print(f"File created: {result.get('file_path')}")
            return True
        else:
            print(f"❌ Build failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Build crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_step_by_step()
    print(f"\n=== Result: {'SUCCESS' if success else 'FAILED'} ===")