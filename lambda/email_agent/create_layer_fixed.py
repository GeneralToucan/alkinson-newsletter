"""
Fixed Lambda Layer Creator - Uses pip download for reliability

This downloads Linux wheels and extracts them properly.
"""

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def main():
    print("Creating Lambda Layer (Fixed Method)...")
    print("=" * 60)
    
    current_dir = Path(__file__).parent
    layer_dir = current_dir / "layer"
    python_dir = layer_dir / "python"
    wheels_dir = current_dir / "wheels_temp"
    
    # Clean up
    for dir_path in [layer_dir, wheels_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
    
    python_dir.mkdir(parents=True)
    wheels_dir.mkdir()
    print("✓ Created directories")
    
    # Download wheels for Linux
    print("\nDownloading Linux wheels...")
    requirements_file = current_dir / "requirements.txt"
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "download",
            "-r", str(requirements_file),
            "--platform", "manylinux2014_x86_64",
            "--python-version", "3.11",
            "--only-binary=:all:",
            "--dest", str(wheels_dir)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"  ⚠️ Download with platform failed:")
            print(result.stderr)
            print("\n  Trying without platform flag...")
            
            # Try without platform flag
            subprocess.check_call([
                sys.executable, "-m", "pip", "download",
                "-r", str(requirements_file),
                "--dest", str(wheels_dir)
            ])
        
        print("  ✓ Downloaded wheels")
        
    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        print("\n  Falling back to direct install...")
        
        # Fallback: install directly
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", str(requirements_file),
                "-t", str(python_dir)
            ])
            print("  ✓ Installed directly")
            
            # Skip to ZIP creation
            wheels_dir = None
            
        except Exception as e2:
            print(f"  ✗ Install failed: {e2}")
            return False
    
    # Extract wheels if we downloaded them
    if wheels_dir and wheels_dir.exists():
        print("\nExtracting wheels...")
        wheel_files = list(wheels_dir.glob("*.whl"))
        
        if not wheel_files:
            print("  ⚠️ No wheel files found!")
            return False
        
        for wheel_file in wheel_files:
            print(f"  Extracting {wheel_file.name}...")
            try:
                with zipfile.ZipFile(wheel_file, 'r') as zip_ref:
                    # Extract all files
                    zip_ref.extractall(python_dir)
            except Exception as e:
                print(f"    ⚠️ Failed to extract {wheel_file.name}: {e}")
        
        print("  ✓ Extracted all wheels")
        
        # Clean up wheels
        shutil.rmtree(wheels_dir)
    
    # Verify python directory has content
    if not list(python_dir.iterdir()):
        print("\n  ✗ python/ directory is empty!")
        return False
    
    print(f"\n  ✓ python/ directory contains {len(list(python_dir.iterdir()))} items")
    
    # Create ZIP
    print("\nCreating ZIP...")
    zip_name = "email_agent_dependencies_layer"
    zip_path = current_dir / f"{zip_name}.zip"
    
    if zip_path.exists():
        zip_path.unlink()
    
    # Create ZIP with correct structure
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, layer_dir)
                zipf.write(file_path, arcname)
    
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {zip_name}.zip ({size_mb:.2f} MB)")
    
    # Verify ZIP structure
    print("\nVerifying ZIP structure...")
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        files = zipf.namelist()
        has_python_dir = any(f.startswith('python/') for f in files)
        has_pydantic = any('pydantic' in f for f in files)
        
        if not has_python_dir:
            print("  ✗ WARNING: ZIP doesn't have python/ directory!")
        else:
            print("  ✓ ZIP has python/ directory")
        
        if not has_pydantic:
            print("  ✗ WARNING: ZIP doesn't contain pydantic!")
        else:
            print("  ✓ ZIP contains pydantic")
    
    # Clean up
    shutil.rmtree(layer_dir)
    
    print("\n" + "=" * 60)
    print("✓ Layer created!")
    print(f"\nFile: {zip_path}")
    print(f"Size: {size_mb:.2f} MB")
    
    if size_mb < 1:
        print("\n⚠️  WARNING: File size is very small!")
        print("Dependencies may not have installed correctly.")
        print("Try running with administrator privileges.")
    
    print("\nNext steps:")
    print("1. Go to Lambda Console → Layers")
    print("2. DELETE old 'email-agent-dependencies' layer if it exists")
    print("3. Click 'Create layer'")
    print("4. Name: email-agent-dependencies")
    print("5. Upload this ZIP file")
    print("6. Compatible runtimes: Python 3.11")
    print("7. Click 'Create'")
    print("\n8. Go to your Lambda function")
    print("9. Remove old layer if attached")
    print("10. Add the new layer")
    print("11. Test!")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
