def test_package_import_is_lightweight():
    import emotional_model_fls

    assert emotional_model_fls.__version__
