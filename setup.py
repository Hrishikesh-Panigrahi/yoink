from pathlib import Path

from setuptools import setup

ROOT = Path(__file__).resolve().parent
version_ns = {}
exec((ROOT / "src" / "version.py").read_text(encoding="utf-8"), version_ns)

setup(
    name="yoink",
    version=version_ns["__version__"],
    py_modules=["main", "main_window", "bridge", "workers", "db", "models", "version"],
    packages=["torrents", "search", "providers", "utils"],
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        'PyQt6>=6.4.0',
        'PyQt6-WebEngine>=6.4.0',
        'libtorrent>=2.0.0',
        'sqlalchemy>=2.0.0',
        'requests>=2.31.0',
        'beautifulsoup4>=4.11.0',
        'pillow==10.0.0',
        'python-magic==0.4.27',
        'aiohttp==3.11.16',
        'cloudscraper>=1.2.71',
    ],
    entry_points={
        'console_scripts': [
            'yoink=main:main',
        ],
    },
    python_requires='>=3.11',
    author="Yoink Contributors",
    description="Yoink - a modern torrent client. Just yoink it from the swarm.",
    long_description=(ROOT / 'README.md').read_text(encoding='utf-8'),
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="torrent client downloader",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: File Transfer Protocol (FTP)",
    ],
) 