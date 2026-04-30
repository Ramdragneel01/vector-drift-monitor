import os
import sys

# Ensure src/ is on sys.path so editable install isn't required for unit testing.
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)
