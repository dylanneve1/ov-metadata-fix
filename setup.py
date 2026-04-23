from setuptools import setup


setup(
    name="ov-metadata-fix",
    version="0.3.0",
    description="Patch openvino dist-info METADATA Version on Python startup (CI check workaround).",
    packages=["ov_metadata_fix"],
    data_files=[("", ["ov_metadata_fix.pth"])],
)
