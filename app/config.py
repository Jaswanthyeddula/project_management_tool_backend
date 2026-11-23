import os
import ssl
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "development-secret-change-me-32-bytes")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "development-jwt-secret-change-me-32-bytes")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "pm_tool")
    DB_SSL_CA = os.environ.get("DB_SSL_CA")

    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self):
        """Configure connection pool and SSL options for database."""
        options = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
        }

        # Add SSL configuration for TiDB Cloud or other SSL-enabled databases
        if self.DB_SSL_CA:
            connect_args = {
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
                "ssl_ca": self.DB_SSL_CA,
            }
            options["connect_args"] = connect_args

        return options

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        if not self.DB_USER or not self.DB_HOST:
            raise RuntimeError(
                "MySQL configuration is missing. Set DB_USER and DB_HOST before running the app."
            )

        uri = (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
        return uri


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        secret_key = os.environ.get("SECRET_KEY", "")
        jwt_secret_key = os.environ.get("JWT_SECRET_KEY", "")
        if not secret_key or "change-me" in secret_key:
            raise RuntimeError(
                "SECRET_KEY must be securely set via environment variable in production (not default change-me)."
            )
        if not jwt_secret_key or "change-me" in jwt_secret_key:
            raise RuntimeError(
                "JWT_SECRET_KEY must be securely set via environment variable in production (not default change-me)."
            )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}