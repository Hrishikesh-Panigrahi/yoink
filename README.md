# Torrent App

A modern torrent client with search functionality built using PyQt6 and libtorrent.

## Features

- Search and download torrents
- Modern and intuitive user interface
- Download speed monitoring
- Pause/Resume downloads
- Multiple download directory support
- Download history tracking

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Install from Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/torrent-app.git
cd torrent-app
```

2. Create and activate a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

## Usage

1. Start the application:
```bash
torrent-app
```

2. Use the search bar to find torrents
3. Click "Download" to start downloading
4. Monitor downloads in the "Downloads" tab
5. Change download directory using the "Change Directory" button

## Configuration

- Default download directory: `~/Downloads`
- Database file: `torrent.db` (created in the application directory)
- Log file: `logs/torrent_app.log`

## Development

To contribute to the project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 