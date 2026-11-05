"""Nothing is re-exported here, and that is deliberate.

`benchmark/truth/engine.py` imports `benchmark.generator.documents` for the rendered-label
table, while `benchmark.generator.build` imports `benchmark.truth.rules_eval`. If this file
re-exported `build_case`, then a cold `from benchmark.graders import grade` would run the
generator package initialiser halfway through the truth package's own initialisation and fail
with a partially-initialised-module ImportError. Everything in the repo already imports the
submodule it wants, so the convenience re-export cost a working entry point.
"""
