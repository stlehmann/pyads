import faulthandler

# Emit a Python traceback on segfault instead of a silent crash.
# This helps diagnose any remaining shutdown-time segfaults from the C library.
faulthandler.enable()
