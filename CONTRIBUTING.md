# Contributing

Start with a reproducible issue or a small, focused pull request. Feature requests should describe a concrete use case before proposing a large implementation.

1. Fork and clone the repository.
2. Use Python 3.10+ and install with `python -m pip install -e .`.
3. Add a small regression fixture for the behavior you change.
4. Run `python -m unittest discover -s tests -v`.
5. Describe the behavior, checks performed, and any untested environment in your PR.

Use synthetic fixtures. Do not upload private datasets, medical records, model weights, credentials or tokens. AI-assisted contributions are welcome when disclosed, understood by the contributor, and tested. Do not submit generated bulk changes or make unsupported performance claims.

By contributing, you agree that your contribution will be licensed under the project's MIT license. Please keep discussions respectful and focused on the technical work.
