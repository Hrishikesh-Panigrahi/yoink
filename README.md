# Torrent App

A modern, feature-rich torrent client built with PyQt6 and libtorrent. This application provides a clean, intuitive interface for searching and downloading torrents with advanced features like download management, speed monitoring, and customizable settings.

## Features

- 🔍 Integrated torrent search functionality
- 📥 Fast, non-blocking torrent downloads
- ⏯️ Pause/Resume/Delete torrent operations
- 📊 Real-time download speed and progress monitoring
- 📁 Customizable download directories per torrent
- 📝 Download history tracking
- 🔄 Automatic metadata retrieval
- 💾 Persistent settings and download states
- 🎯 Modern, responsive user interface

## Requirements

- Python 3.8 or higher
- Operating System: macOS, Linux, or Windows
- Internet connection for searching and downloading torrents

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/torrent-app.git
cd torrent-app-mac
```

2. Create and activate a virtual environment:
```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Make sure your virtual environment is activated
2. Run the application:
```bash
# From the project root directory
PYTHONPATH=$PYTHONPATH:. python3 src/main.py
```

## Usage Guide

1. **Search for Torrents**
   - Enter your search query in the search bar
   - Click the search button or press Enter
   - Results will appear in the search tab

2. **Download a Torrent**
   - Click the "Download" button next to a search result
   - The torrent will appear in the Downloads tab
   - Initial metadata download will begin automatically

3. **Manage Downloads**
   - Use the Downloads tab to view all your torrents
   - Pause/Resume: Click the respective buttons
   - Delete: Remove torrents and optionally their files
   - Monitor progress, speed, and estimated time

4. **Change Settings**
   - Set default download directory
   - Configure network settings
   - Manage application preferences

## Project Structure

```
torrent-app-mac/
├── src/
│   ├── core/           # Core functionality
│   ├── database/       # Database models and management
│   ├── gui/           # User interface components
│   └── utils/         # Utility functions
├── requirements.txt   # Project dependencies
└── README.md         # This file
```

## Dependencies

Key dependencies (see requirements.txt for full list):
- PyQt6 (≥6.4.0): GUI framework
- libtorrent (≥2.0.0): Torrent handling
- SQLAlchemy (≥2.0.0): Database management
- requests (≥2.28.0): HTTP client
- beautifulsoup4 (≥4.11.0): Web scraping
- aiohttp (3.11.16): Async HTTP client

## Troubleshooting

1. **Installation Issues**
   - Ensure Python 3.8+ is installed
   - Use a virtual environment
   - Check system dependencies for PyQt6 and libtorrent

2. **Runtime Issues**
   - Check logs in `logs/torrent_app.log`
   - Verify internet connection
   - Ensure write permissions in download directory

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Please ensure your changes:
- Include appropriate tests
- Update documentation
- Follow the existing code style
- Add meaningful commit messages

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Disclaimer

This application is for educational purposes only. Users are responsible for complying with local laws and regulations regarding torrent downloads. 