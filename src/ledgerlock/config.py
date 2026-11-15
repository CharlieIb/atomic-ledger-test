import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://ledgerlock@localhost:5432/ledgerlock",
)
