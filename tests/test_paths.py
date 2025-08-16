from pysigil.paths import user_cache_dir, user_config_dir, user_data_dir


def test_user_dirs_absolute() -> None:
    assert user_config_dir().is_absolute()
    assert user_data_dir().is_absolute()
    assert user_cache_dir().is_absolute()
