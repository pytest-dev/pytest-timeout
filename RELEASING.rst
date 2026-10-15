Releasing
=========

1. Update the version in ``setup.cfg``.
2. Merge the PR to ``main``.
3. Create a `GitHub Release <https://github.com/pytest-dev/pytest-timeout/releases/new>`_
   with tag ``X.Y.Z`` targeting ``main``.
4. The ``Release`` workflow builds the package, checks it, and publishes it
   to PyPI.

Notes for maintainers:

- Publishing uses PyPI `Trusted Publishing
  <https://docs.pypi.org/trusted-publishers/>`_ via the ``release``
  environment: owner ``pytest-dev``, repo ``pytest-timeout``, workflow
  ``release.yaml``, environment ``release``.
- The ``release`` GitHub environment can require maintainer approval
  before the publish job runs.
