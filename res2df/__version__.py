try:
    from .version import version  # type: ignore

    __version__ = version
except ImportError:
    __version__ = "v0.0.0"
