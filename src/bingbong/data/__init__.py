"""Data package for bundled audio files.

Having this file ensures the directory is treated as a package so
`importlib.resources` can reliably locate the wav assets when installed
via wheels built by `uv tool install`.
"""
