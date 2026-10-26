# pytest plugin (loaded with -p from outside the repo): print one function name per (file, suite).
SUITES = ("unit", "integration", "negative", "regression", "reproducibility", "security", "contracts", "simulation")
def pytest_collection_modifyitems(config, items):
    keep = {}
    for item in items:
        for s in SUITES:
            if item.get_closest_marker(s) is not None:
                keep.setdefault((str(item.path), s), item.originalname if hasattr(item, "originalname") else item.name)
    open(config.getoption("--citerift-report") + ".names", "w").write("\n".join(sorted(set(keep.values()))))
