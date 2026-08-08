"""Single source of truth for the application version.

`build.py`, `setup.py`, the About panel, and the auto-updater all read
``__version__`` from here. Bumping the release is a one-line change.
"""

__version__ = "2.1.1"
__app_name__ = "Yoink"
__app_homepage__ = "https://github.com/Hrishikesh-Panigrahi/yoink"
__release_api__ = "https://api.github.com/repos/Hrishikesh-Panigrahi/yoink/releases/latest"
