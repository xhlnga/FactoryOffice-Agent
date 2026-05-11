def pytest_addoption(parser):
    parser.addoption("--rewrite", action="store_true", default=False,
                     help="Enable query rewriting for A/B comparison")
