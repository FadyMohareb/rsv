"""
config.py
=========

This module provides the configuration settings for the application. It defines a
`Config` class that centralizes configuration variables such as the SQLAlchemy
database URI, as well as paths for static and media folders.

Attributes:
    basedir (str): The absolute path of the directory where this configuration file resides.

:author: Kevin
:version: 0.0.1
:date: 2025-02-21
"""

import os


basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    """
    Application configuration class.

    This class defines configuration variables for the application. The values
    are obtained from environment variables with sensible defaults where applicable.

    Attributes:
        SQLALCHEMY_DATABASE_URI (str): The database URI used by SQLAlchemy.
            Retrieved from the "DATABASE_URL" environment variable, or defaults to "sqlite://".
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Flag to disable modification tracking in SQLAlchemy.
        STATIC_FOLDER (str): Path to the static files directory.
        MEDIA_FOLDER (str): Path to the media files directory.
    """
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite://")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STATIC_FOLDER = f"{os.getenv('APP_FOLDER')}/project/static"
    MEDIA_FOLDER = f"{os.getenv('APP_FOLDER')}/project/media"