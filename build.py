#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build():
    """Clean build directories"""
    dirs_to_clean = ['build', 'dist']
    files_to_clean = ['TorrentApp.spec']
    
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
    
    # Build command with all necessary options
    cmd = [
        'pyinstaller',
        '--name=TorrentApp',
        '--onefile',
        '--windowed',
        '--clean',
        f'--paths={src_path}',  # Add src directory to Python path
        '--add-data=src/resources:resources',  # Include resources directory
        '--hidden-import=PyQt6',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=gui',
        '--hidden-import=gui.main_window',
        '--hidden-import=gui.torrent_list',
        '--hidden-import=gui.torrent_item',
        '--hidden-import=gui.torrent_details',
        '--hidden-import=gui.settings_dialog',
        '--hidden-import=gui.search_dialog',
        '--hidden-import=gui.torrent_progress',
        '--hidden-import=core',
        '--hidden-import=core.torrent_manager',
        '--hidden-import=core.torrent_searcher',
        '--hidden-import=database',
        '--hidden-import=database.database',
        '--hidden-import=database.models',
        '--hidden-import=utils',
        '--hidden-import=utils.logger',
        '--hidden-import=libtorrent',
        '--hidden-import=sqlalchemy',
        '--hidden-import=requests',
        '--hidden-import=bs4',
        '--hidden-import=PIL',
        '--hidden-import=magic',
        '--hidden-import=aiohttp',
        '--hidden-import=asyncio',
        '--hidden-import=json',
        '--hidden-import=logging',
        '--hidden-import=os',
        '--hidden-import=sys',
        '--hidden-import=pathlib',
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