import sys
from pathlib import Path

# The grader is run as `python -m grader.agreement` from the task directory; tests import it the same way.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
