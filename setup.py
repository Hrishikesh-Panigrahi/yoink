from setuptools import setup, find_packages

setup(
    name="torrent-app",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.4.0",
        "libtorrent>=2.0.0",
        "sqlalchemy>=2.0.0",
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
    ],
    entry_points={
        "console_scripts": [
            "torrent-app=src.main:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A modern torrent client with search functionality",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="torrent, download, p2p, client",
    url="https://github.com/yourusername/torrent-app",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
) 