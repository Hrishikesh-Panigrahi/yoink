from setuptools import setup, find_packages

setup(
    name="torrent-app",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'PyQt6>=6.4.0',
        'libtorrent>=2.0.0',
        'sqlalchemy>=2.0.0',
        'requests>=2.28.0',
        'beautifulsoup4>=4.11.0',
        'pillow==10.0.0',
        'python-magic==0.4.27',
        'aiohttp==3.11.16'
    ],
    entry_points={
        'console_scripts': [
            'torrent-app=src.main:main',
        ],
    },
    python_requires='>=3.8',
    author="Torrent App Contributors",
    description="A modern torrent client with search functionality",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="torrent client downloader",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Topic :: Internet :: File Transfer Protocol (FTP)",
    ],
) 