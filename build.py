#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build():
    """Clean build directories"""
    dirs_to_clean = ['build', 'dist']
    files_to_clean = ['TorrentApp.spec', 'Yoink.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned {dir_name}/")
    
    for file_name in files_to_clean:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"Cleaned {file_name}")

def build_app():
    """Build the application using PyInstaller"""
    # Install PyInstaller if not already installed
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    
    # Get the absolute path to the src directory
    src_path = os.path.abspath('src')
    
    # Add src directory to Python path
    sys.path.insert(0, src_path)
    
    # PyInstaller uses os-specific path separators in --add-data ("," on Win, ":" elsewhere)
    sep = ';' if os.name == 'nt' else ':'

    cmd = [
        'pyinstaller',
        '--name=Yoink',
        '--onefile',
        '--windowed',
        '--clean',
        f'--paths={src_path}',
        f'--add-data=src/resources{sep}resources',
        f'--add-data=src/web{sep}web',
        f'--add-data=src/vendor{sep}vendor',
        '--hidden-import=PyQt6',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtWebEngineWidgets',
        '--hidden-import=PyQt6.QtWebEngineCore',
        '--hidden-import=PyQt6.QtWebChannel',
        '--hidden-import=main_window',
        '--hidden-import=bridge',
        '--hidden-import=workers',
        '--hidden-import=db',
        '--hidden-import=models',
        '--hidden-import=torrents',
        '--hidden-import=torrents.session',
        '--hidden-import=torrents.actions',
        '--hidden-import=torrents.state',
        '--hidden-import=torrents.persistence',
        '--hidden-import=torrents.dto',
        '--hidden-import=search',
        '--hidden-import=search.enums',
        '--hidden-import=search.dto',
        '--hidden-import=search.ranking',
        '--hidden-import=providers',
        '--hidden-import=providers.yts',
        '--hidden-import=providers.pirate_bay',
        '--hidden-import=providers.torrent_api_py',
        '--hidden-import=utils',
        '--hidden-import=utils.logger',
        '--hidden-import=utils.format',
        '--hidden-import=utils.paths',
        '--hidden-import=utils.magnets',
        '--hidden-import=libtorrent',
        '--hidden-import=sqlalchemy',
        '--hidden-import=requests',
        '--hidden-import=bs4',
        '--hidden-import=PIL',
        '--hidden-import=magic',
        '--hidden-import=aiohttp',
        'src/main.py'
    ]
    
    # Run PyInstaller
    subprocess.run(cmd, check=True)
    print("Build completed successfully!")

def main():
    try:
        clean_build()
        build_app()
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 