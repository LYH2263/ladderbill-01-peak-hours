import os
import tempfile

# Point the app at a throwaway database before any app.* module is imported.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="ladderbill-test-")
