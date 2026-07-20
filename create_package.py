import os
import zipfile

EXCLUDE_DIRS = {'node_modules', 'dist', '.git', '.trae', '__pycache__', 'data', 'uploads', '.venv', '.pytest_cache'}
EXCLUDE_FILES = {'.env', '.gitignore', 'node.msi', 'test.db', 'exercise.db', 'create_package.py', 'create_package.ps1', 'deploy.py', 'deploy.sh', 'DEPLOY_MANUAL.md', 'fuxi-deploy.zip'}

package_name = 'fuxi-deploy.zip'

if os.path.exists(package_name):
    os.remove(package_name)

print(f'创建部署包: {package_name}')
count = 0

with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file in EXCLUDE_FILES or file.endswith('.pyc') or file.endswith('.pyo'):
                continue
            
            local_path = os.path.join(root, file)
            arcname = os.path.relpath(local_path, '.')
            
            zf.write(local_path, arcname)
            count += 1
            print(f'  添加: {arcname}')

size = os.path.getsize(package_name) / 1024
print(f'\n部署包已创建: {package_name} ({count} 个文件, {int(size)} KB)')
