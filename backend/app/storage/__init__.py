"""Application-managed storage for uploaded datasets and generated artifacts.

Files are always written under app.core.config.Settings.uploads_dir /
artifacts_dir (created on startup), never to an arbitrary caller-supplied
path, so upload/export endpoints cannot be used for path traversal.
"""
