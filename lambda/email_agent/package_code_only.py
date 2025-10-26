"""
Package Email Agent Lambda code without dependencies.

Use this when you're using a Lambda Layer for dependencies.
This creates a smaller ZIP with just your code.

Usage:
    python package_code_only.py
"""

import shutil
from pathlib import Path
import sys


def main():
    print("Creating code-only package for Email Agent...")
    print("=" * 60)
    
    current_dir = Path(__file__).parent
    deployment_dir = current_dir / "deployment"
    shared_dir = current_dir.parent / "shared"
    
    # Clean up old deployment directory
    if deployment_dir.exists():
        print("Cleaning up old deployment directory...")
        shutil.rmtree(deployment_dir)
    
    # Create deployment directory
    deployment_dir.mkdir()
    print("✓ Created deployment directory")
    
    # Copy Lambda code files
    lambda_files = [
        "lambda_function.py",
        "subscriber_manager.py",
        "email_formatter.py",
        "email_sender.py",
        "__init__.py"
    ]
    
    print("\nCopying Lambda code files...")
    for file in lambda_files:
        src = current_dir / file
        if src.exists():
            shutil.copy2(src, deployment_dir / file)
            print(f"  ✓ {file}")
        else:
            print(f"  ⚠ {file} not found (skipping)")
    
    # Copy shared utilities
    print("\nCopying shared utilities...")
    shared_dest = deployment_dir / "shared"
    if shared_dir.exists():
        shutil.copytree(shared_dir, shared_dest)
        print("  ✓ Copied shared/ directory")
    else:
        print("  ⚠ shared/ directory not found")
    
    # Create ZIP file
    print("\nCreating ZIP file...")
    zip_name = "email_agent_code_only"
    zip_path = current_dir / f"{zip_name}.zip"
    
    # Remove old ZIP if exists
    if zip_path.exists():
        zip_path.unlink()
    
    # Create ZIP from deployment directory
    shutil.make_archive(
        str(current_dir / zip_name),
        'zip',
        str(deployment_dir)
    )
    
    # Get ZIP file size
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {zip_name}.zip ({zip_size_mb:.2f} MB)")
    
    # Clean up deployment directory
    print("\nCleaning up...")
    shutil.rmtree(deployment_dir)
    print("  ✓ Removed temporary deployment directory")
    
    # Success message
    print("\n" + "=" * 60)
    print("✓ Code-only package ready!")
    print(f"\nFile: {zip_path}")
    print(f"Size: {zip_size_mb:.2f} MB")
    print("\nThis package contains ONLY your code (no dependencies).")
    print("Make sure you've created and attached the Lambda Layer!")
    print("\nNext steps:")
    print("1. Go to AWS Lambda Console")
    print("2. Open your Email Agent function")
    print("3. Click 'Upload from' → '.zip file'")
    print("4. Select email_agent_code_only.zip")
    print("5. Click 'Save'")
    print("\nMake sure the Lambda Layer is attached:")
    print("- Check 'Layers' section shows 'email-agent-dependencies'")
    print("- If not, add it via 'Add a layer' button")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
