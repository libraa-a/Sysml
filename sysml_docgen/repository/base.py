"""Shared repository abstractions and error types."""

from __future__ import annotations

from ..repository_contract import RepositoryStore


class StoreError(Exception):
    status_code = 400


class NotFoundError(StoreError):
    status_code = 404


class ConflictError(StoreError):
    status_code = 409


class ForbiddenError(StoreError):
    status_code = 403


__all__ = ["RepositoryStore", "StoreError", "NotFoundError", "ConflictError", "ForbiddenError"]
