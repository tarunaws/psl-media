# Offline install (Wheelhouse)

Use this when `pip install` fails with `403 Forbidden` to `files.pythonhosted.org`.

This repo’s primary dev setup is macOS on Apple Silicon (arm64) with Python 3.13 in `code/.venv`. For the smoothest offline install, build the wheelhouse on the same OS/CPU/Python (macOS + arm64 + Python 3.13).

## 1) Build the wheelhouse (on an unblocked network)

Run these from the repo root.

- Confirm you’re on Apple Silicon: `uname -m` should be `arm64`.
- Use Python 3.13 (recommended: same OS/CPU/Python as the target machine)
- Download wheels into a folder:

```bash
python3.13 -m pip install -U pip
python3.13 code/scripts/build_wheelhouse.py --output-dir code/.wheelhouse
```

Optional ML deps:

```bash
python3.13 code/scripts/build_wheelhouse.py --output-dir code/.wheelhouse --optional-ml
```

If a package has no wheel and you are okay building from source, add `--allow-source`.

## 2) Transfer the wheelhouse to the blocked machine

Zip/copy the folder `code/.wheelhouse/` onto the blocked machine.

## 3) Install into the repo’s shared venv (on the blocked machine)

From `code/`:

```bash
rm -rf .venv
python3.13 -m venv .venv
./.venv/bin/python3 -m pip install -U pip
./.venv/bin/python3 scripts/install_wheelhouse.py --wheelhouse .wheelhouse
```

Then restart:

```bash
./stop-all.sh
./start-all.sh
```
