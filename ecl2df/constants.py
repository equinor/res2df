"""Constants for use in ecl2df."""

# This is a magic filename that means read/write from/to stdout
# This makes it impossible to write to a file called "-" on disk
# but that would anyway create a lot of other problems in the shell.
MAGIC_STDOUT: str = "-"
