import pytest

from app.config import Settings


def _prod_kwargs(**overrides):
    base = dict(
        _env_file=None,
        environment="production",
        secret_key="x" * 40,
        refresh_secret_key="y" * 40,
        superadmin_password="a-real-password",
        superadmin_secret_key="z" * 40,
    )
    base.update(overrides)
    return base


def test_production_boot_refused_with_placeholder_secret():
    with pytest.raises(ValueError, match="placeholder"):
        Settings(**_prod_kwargs(secret_key="change-me-in-production"))


def test_production_boot_refused_with_short_secret():
    with pytest.raises(ValueError, match="at least 32"):
        Settings(**_prod_kwargs(secret_key="short"))


def test_production_boot_refused_when_keys_identical():
    with pytest.raises(ValueError, match="must differ"):
        Settings(**_prod_kwargs(refresh_secret_key="x" * 40))


def test_production_boot_allowed_with_real_secrets():
    s = Settings(**_prod_kwargs())
    assert s.is_production


def test_development_boot_allowed_with_defaults():
    s = Settings(_env_file=None, environment="development")
    assert not s.is_production
