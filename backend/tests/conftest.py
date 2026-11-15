import os
import sys

# Force mocked LLM provider and in-memory DB for all automated test runs
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

settings.ENVIRONMENT = "test"
settings.LLM_PROVIDER = "mock"
settings.DATABASE_URL = "sqlite:///:memory:"
