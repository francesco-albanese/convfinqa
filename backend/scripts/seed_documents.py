"""Entrypoint wrapper — logic lives in convfinqa.adapters.persistence.documents_seeder."""

from __future__ import annotations

import sys

from convfinqa.adapters.persistence.documents_seeder import main

if __name__ == "__main__":
    sys.exit(main())
