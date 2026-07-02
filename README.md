<p align="center">
  <picture>
    <img src="https://raw.githubusercontent.com/ecmwf/logos/feature/add-logo-pyflow_wellies-20250501113719/logos/pyflow/logo_pyflow.png" height="240">
  </picture>
</p>
<h1 align="center" style="margin-top: 0.001em; margin-bottom: 0.5em;">Pyflow</h1>

<p align="center">
  <a href="https://github.com/ecmwf/codex/raw/refs/heads/main/ESEE">
    <img src="https://github.com/ecmwf/codex/raw/refs/heads/main/ESEE/foundation_badge.svg" alt="ECMWF Software EnginE">
  </a>
  <a href="https://github.com/ecmwf/codex/raw/refs/heads/main/Project Maturity">
    <img src="https://github.com/ecmwf/codex/raw/refs/heads/main/Project Maturity/graduated_badge.svg" alt="Maturity Level">
  </a>
  <a href="https://opensource.org/licenses/apache-2-0">
    <img src="https://img.shields.io/badge/Licence-Apache 2.0-blue.svg" alt="Licence">
  </a>
  <a href="https://github.com/ecmwf/tracksuite/releases">
    <img src="https://img.shields.io/github/v/release/ecmwf/tracksuite?color=purple&label=Release" alt="Latest Release">
  </a>
</p>

<p align="center">
  <!-- <a href="#quick-start">Quick Start</a>
  • -->
  <a href="#installation">Installation</a>
  •
  <a href="#documentation">Documentation</a>
  •
  <a href="#License">License</a>
</p>

**Pyflow** is a high level Python interface to ecFlow allowing the creation of ecFlow suites in a modular and "pythonic" way.


## Installation

To install pyflow using conda (including ecFlow):

    conda env create -n pyflow -f environment.yml

To install pyflow using pip (requires a local installation of ecFlow):

    pip install pyflow-workflow-generator

## Documentation

The documentation can be found at <https://pyflow-workflow-generator.readthedocs.io>.

## QA Checks (CI-equivalent)

The CI `qa` job runs the following checks, in order:

1. `isort --check .`
2. `black --check .`
3. `flake8 .`

This repository includes a matching pre-commit configuration in
`.pre-commit-config.yaml` using standard upstream hooks, pinned to the
tool versions from the CI run:

- `isort==8.0.1`
- `black==26.5.1`
- `flake8==7.3.0`

Run locally:

```bash
python -m pip install ".[dev]"
pre-commit run --all-files
```

The hooks are split into three sequential checks (isort, then black, then
flake8) to avoid conflicts and to match CI behavior. Running `isort` before
`black` prevents import-format churn, and running `flake8` last ensures linting
sees code after formatting checks.


## License
[Apache License 2.0](LICENSE) In applying this licence, ECMWF does not waive the privileges and immunities 
granted to it by virtue of its status as an intergovernmental organisation nor does it submit to any jurisdiction.
