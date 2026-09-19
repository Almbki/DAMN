"""Cross-cutting concerns: configuration, security primitives, logging.

This package MUST NOT import FastAPI, SQLAlchemy or any workspace module at
import time so that the domain and ML layers can depend on it safely.
"""
