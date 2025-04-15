# Torrent Downloader

A modern, high-performance torrent client built with PyQt6 and libtorrent-python. This application provides a clean, intuitive interface for searching, downloading, and managing torrents with advanced features like real-time progress monitoring, download management, and customizable settings.

## Features

- 🔍 Integrated torrent search with multiple providers
- 📥 Fast, non-blocking torrent downloads with libtorrent
- ⏯️ Complete torrent management (Add/Pause/Resume/Delete)
- 📊 Real-time statistics (speed, progress, peers, etc.)
- 📁 Customizable download paths per torrent
- 📝 Persistent download history and states
- 🔄 Automatic metadata retrieval and updates
- 💾 SQLite-based state management
- 🎯 Modern PyQt6-based user interface
- 🔒 Secure and private downloads

## Screenshots

[Coming soon]

## Requirements

- Python 3.9 or higher
- Operating System: macOS (primary), Linux (supported), Windows (partial)
- Internet connection
- 100MB disk space (excluding downloads)

## Installation

1. Clone the repository:
```bash
git clone git@tree.mn:pureplay/torrent-downloader.git
cd torrent-downloader
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Ensure your virtual environment is activated:
```bash
source venv/bin/activate  # On macOS/Linux
```

2. Run the application:
```bash
PYTHONPATH=$PYTHONPATH:. python3 src/main.py
```

## Development Setup

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Set up pre-commit hooks:
```bash
pre-commit install
```

3. Run tests:
```bash
pytest tests/
```

## Project Structure

```
torrent-downloader/
├── src/
│   ├── core/           # Core torrent functionality
│   │   ├── torrent_manager.py    # Main torrent management
│   │   ├── torrent_session.py    # libtorrent session handling
│   │   └── torrent_operations.py # Torrent operations facade
│   ├── database/       # Database management
│   │   ├── models.py   # SQLAlchemy models
│   │   └── database.py # Database connection handling
│   ├── gui/           # PyQt6 UI components
│   │   ├── main_window.py      # Main application window
│   │   ├── torrent_list.py     # Torrent list widget
│   │   └── settings_dialog.py  # Settings dialog
│   └── utils/         # Utility functions
├── tests/            # Test suite
├── requirements.txt  # Production dependencies
└── README.md        # This file
```

## Key Dependencies

- **PyQt6** (≥6.4.0): Modern GUI framework
- **libtorrent-python** (≥2.0.0): Core torrent functionality
- **SQLAlchemy** (≥2.0.0): Database ORM
- **aiohttp** (≥3.11.16): Async HTTP client
- **beautifulsoup4** (≥4.11.0): Search results parsing

## Configuration

The application can be configured through:
1. GUI Settings dialog
2. Environment variables:
   - `TORRENT_DOWNLOAD_PATH`: Default download directory
   - `TORRENT_MAX_CONNECTIONS`: Maximum peer connections
   - `TORRENT_PORT_RANGE`: Port range for incoming connections

## Troubleshooting

1. **Installation Issues**
   - Ensure Python 3.9+ is installed: `python3 --version`
   - Use a fresh virtual environment
   - On macOS, you might need: `brew install qt6`

2. **Runtime Issues**
   - Check logs in `logs/torrent_app.log`
   - Verify network connectivity
   - Ensure sufficient disk space
   - Check port forwarding if needed

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a merge request

Please ensure your changes:
- Follow PEP 8 style guide
- Include unit tests
- Update documentation
- Add type hints
- Use meaningful commit messages

## Security

- All network traffic is encrypted
- No data is sent to external servers
- Downloads are isolated by default
- Automatic updates are disabled
- No telemetry collection

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This application is for educational purposes only. Users are responsible for:
- Complying with local laws and regulations
- Ensuring downloaded content is legal
- Managing network bandwidth appropriately
- Securing their system and data 