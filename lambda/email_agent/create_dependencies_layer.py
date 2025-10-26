"""
Create Lambda Layer with dependencies for Email Agent.

This creates a separate ZIP file with just the Python dependencies,
which can be uploaded as a Lambda Layer. This is more reliable than
including dependencies in the main Lambda ZIP.

Usage:
    python create_dependencies_layer.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    print("Creating Lambda Layer for Email Agent dependencies...")
    print("=" * 60)
    
    current_dir = Path(__file__).parent
    layer_dir = current_dir / "layer"
    python_dir = layer_dir / "python"
    
    # Clean up old layer directory
    if layer_dir.exists():
        print("Cleaning up old layer directory...")
        shutil.rmtree(layer_dir)
    
    # Create layer directory structure
    python_dir.mkdir(parents=True)
    print("✓ Created layer directory structure")
    
    # Install dependencies
    print("\nInstalling dependencies for Lambda Layer...")
    requirements_file = current_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print("✗ requirements.txt not found")
        return False
    
    try:
        print("  Installing for Linux/x86_64 (Lambda runtime)...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "-r", str(requirements_file),
            "-t", str(python_dir),
            "--platform", "manylinux2014_x86_64",
            "--implementation", "cp",
            "--python-version", "3.11",
            "--only-binary=:all:",
            "--upgrade"
        ])
        print("  ✓ Installed dependencies")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ Platform-specific install failed: {e}")
        print("  Trying standard install...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", str(requirements_file),
                "-t", str(python_dir),
                "--upgrade"
            ])
            print("  ✓ Installed dependencies (standard method)")
        except subprocess.CalledProcessError as e2:
            print(f"  ✗ Failed to install dependencies: {e2}")
            return False
    
    # Create ZIP file
    print("\nCreating layer ZIP file...")
    zip_name = "email_agent_dependencies_layer"
    zip_path = current_dir / f"{zip_name}.zip"
    
    # Remove old ZIP if exists
    if zip_path.exists():
        zip_path.unlink()
    
    # Create ZIP from layer directory
    shutil.make_archive(
        str(current_dir / zip_name),
        'zip',
        str(layer_dir)
    )
    
    # Get ZIP file size
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {zip_name}.zip ({zip_size_mb:.2f} MB)")
    
    # Clean up layer directory
    print("\nCleaning up...")
    shutil.rmtree(layer_dir)
    print("  ✓ Removed temporary layer directory")
    
    # Success message
    print("\n" + "=" * 60)
    print("✓ Lambda Layer package ready!")
    print(f"\nFile: {zip_path}")
    print(f"Size: {zip_size_mb:.2f} MB")
    print("\nNext steps:")
    print("1. Go to AWS Lambda Console")
    print("2. Click 'Layers' in left menu")
    print("3. Click 'Create layer'")
    print("4. Name: email-agent-dependencies")
    print("5. Upload email_agent_dependencies_layer.zip")
    print("6. Compatible runtimes: Python 3.11")
    print("7. Click 'Create'")
    print("\nThen attach the layer to your Lambda function:")
    print("1. Open your Email Agent function")
    print("2. Scroll to 'Layers' section")
    print("3. Click 'Add a layer'")
    print("4. Select 'Custom layers'")
    print("5. Choose 'email-agent-dependencies'")
    print("6. Click 'Add'")
    print("\nSee PACKAGING_TROUBLESHOOTING.md for detailed instructions.")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
