"""
Package Lambda function for manual upload to AWS Console
Creates a ZIP file ready for deployment
"""

import os
import shutil
import zipfile
import subprocess
import sys

def create_deployment_package():
    """Create a deployment package for Lambda"""
    
    print("📦 Creating Lambda deployment package...")
    
    # Create deployment directory
    deploy_dir = "deployment"
    if os.path.exists(deploy_dir):
        print(f"  Removing existing {deploy_dir} directory...")
        shutil.rmtree(deploy_dir)
    
    os.makedirs(deploy_dir)
    print(f"  ✓ Created {deploy_dir} directory")
    
    # Copy Lambda function files
    print("  Copying Lambda function files...")
    files_to_copy = [
        'lambda_function.py',
        'content_gatherer.py',
        'bedrock_summarizer.py',
        'content_processor.py'
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy(file, deploy_dir)
            print(f"    ✓ Copied {file}")
        else:
            print(f"    ⚠️  Warning: {file} not found")
    
    # Install dependencies
    print("  Installing dependencies...")
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--target', deploy_dir],
            check=True,
            capture_output=True
        )
        print("    ✓ Dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Error installing dependencies: {e}")
        return False
    
    # Create ZIP file
    print("  Creating ZIP file...")
    zip_filename = 'content_agent_lambda.zip'
    
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, deploy_dir)
                zipf.write(file_path, arcname)
                
    print(f"    ✓ Created {zip_filename}")
    
    # Get file size
    size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
    print(f"    📊 Package size: {size_mb:.2f} MB")
    
    # Clean up deployment directory
    print("  Cleaning up...")
    shutil.rmtree(deploy_dir)
    print("    ✓ Removed temporary files")
    
    print(f"\n✅ Deployment package created: {zip_filename}")
    print(f"\n📋 Next steps:")
    print(f"1. Go to AWS Lambda Console")
    print(f"2. Find your 'content_agent' Lambda function")
    print(f"3. Click 'Upload from' -> '.zip file'")
    print(f"4. Select {zip_filename}")
    print(f"5. Click 'Save'")
    print(f"6. Configure environment variables (see MANUAL_DEPLOYMENT_GUIDE.md)")
    
    return True

if __name__ == '__main__':
    try:
        success = create_deployment_package()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
