# Docker-based testing for Sigil

This directory provides a lightweight container workflow to run the test suite
and experiment with the CLI in isolation.

## Build image & run unit tests
```sh
cd tests/docker
./run_pytest.sh
```

## Quick one-off CLI inside container
```sh
docker run --rm -it sigil-test bash
```

## Headless secrets demo
```sh
./smoke_cli.sh
```

### Mount the repo for rapid development
```sh
docker run --rm -it -v "$(pwd)":/app sigil-test bash
pip install -e .  # re-install after edits
```

### GitHub Actions example
```yaml
jobs:
  docker-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Sigil tests in Docker
        run: tests/docker/run_pytest.sh
```
