# Contributing

1. Create a focused branch and keep real documents, credentials, certificates, and build outputs outside the repository.
2. Use synthetic PDFs generated inside tests.
3. Run `python -m unittest discover -s tests -v` and `python -m compileall -q main.py backend tests`.
4. Explain changes to PDF structure, signature revisions, token selection, or credential handling in the pull request.

Changes that touch signing behavior should be verified with a disposable test certificate before they are used with an organization certificate.
