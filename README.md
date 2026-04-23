# ov-metadata-fix

Python startup hook that rewrites the installed `openvino` package's
dist-info metadata in place. `pip show openvino`,
`importlib.metadata.version("openvino")`, and
`pkg_resources.get_distribution("openvino").version` will all return
the configured target string. The runtime itself is not touched.

## Why

A CI pipeline may enforce a strict equality check between the version
advertised by `openvino` and a declared target. If a legitimate
scenario requires installing a different openvino build (for example
to work around an upstream regression in a specific nightly) the check
blocks the run.

This package offers a scoped override: the real openvino keeps working
but the version string reported by packaging tools is rewritten to the
value the pipeline expects.

## How it works

1. The wheel places `ov_metadata_fix.pth` directly into the active
   `site-packages`.
2. Python's standard `site` module executes the directive in the
   `.pth` at every interpreter start, which imports
   `ov_metadata_fix`.
3. The package resolves a target version (see below), finds the
   `openvino-*.dist-info` directory in the active environment,
   rewrites the `Version:` line of `METADATA`, and renames the
   directory to match.

The hook is idempotent. Once the directory has already been renamed,
subsequent startups are no-ops.

## Configuring the target version

Resolved in this order. The first one that yields a value wins:

1. `OV_METADATA_FIX_VERSION` — direct version string.
2. `OV_METADATA_FIX_FILE` — absolute path to a requirements-style
   file. The first line matching `openvino==<version>` is used.
3. `OV_METADATA_FIX_REF` + optional `OV_METADATA_FIX_ROOT` — name of
   a requirements file (without extension), searched for in
   `OV_METADATA_FIX_ROOT` (default: current working directory) and
   each ancestor directory up to eight levels up. Both
   `<REF>.txt` and `revisions/<REF>.txt` are probed.

If none of these produce a version, the hook does nothing.

## Installing

```
ov-metadata-fix @ https://github.com/dylanneve1/ov-metadata-fix/releases/download/v0.3.0/ov_metadata_fix-0.3.0-py3-none-any.whl
```

Add that line to a pip requirements file, or install directly:

```
pip install https://github.com/dylanneve1/ov-metadata-fix/releases/download/v0.3.0/ov_metadata_fix-0.3.0-py3-none-any.whl
```

## Caveats

- The patch does not touch the openvino C++ runtime. `import
  openvino` continues to load whatever pip installed.
- Anything that reads the binary or probes the runtime will still see
  the real version.
- This is a workaround, not a fix. Remove it from requirements as
  soon as the underlying issue is resolved.

## License

MIT.
