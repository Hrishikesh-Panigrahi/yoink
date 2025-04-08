from setuptools import setup, find_packages

setup(
    name="torrent-app",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "libtorrent==2.0.11",
        "PyQt6==6.9.0",
        "SQLAlchemy==2.0.0",
        "requests==2.31.0",
        "pillow==10.0.0",
        "python-magic==0.4.27",
        "aiohttp==3.11.16",
        "beautifulsoup4==4.13.3"
    ],
    python_requires=">=3.8",
) 