from __future__ import annotations

from typing import Any

from sqlalchemy.ext.declarative import declarative_base

import ckan.plugins.toolkit as tk

Base: Any

Base = tk.BaseModel if hasattr(tk, "BaseModel") else declarative_base()
