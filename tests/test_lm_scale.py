def test_690b_config_has_690b_parameters_and_tiny_version_runs():
    from euresis.lm.scale import CONFIG_690B, abstract_param_count, requirements, smoke_test
    n = abstract_param_count(CONFIG_690B)
    assert 689.5e9 < n < 691e9
    assert requirements(n)["weights_bf16_tb"] > 1.3
    s = smoke_test()
    assert s["finite"] and s["logits_shape"] == (2, 16, 512)
