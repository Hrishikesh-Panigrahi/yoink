# Torrent App for macOS

A modern torrent client for macOS with a beautiful user interface.

## Features

- Search and download torrents
- Pause, resume, and delete torrents
- View seeds and peers information
- Preview files before downloading
- Modern and intuitive user interface

## Requirements

- Python 3.8 or higher
- macOS 10.15 or higher

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/torrent-app-mac.git
cd torrent-app-mac
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the App

```bash
python src/main.py
```

## Project Structure

```
torrent-app-mac/
├── src/
│   ├── core/          # Core torrent functionality
│   ├── gui/           # User interface components
│   ├── database/      # Database models and operations
│   └── utils/         # Utility functions
├── tests/             # Test files
├── requirements.txt   # Project dependencies
└── README.md         # This file
```

## License

MIT License 