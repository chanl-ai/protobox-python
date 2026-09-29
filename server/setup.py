#!/usr/bin/env python3
from setuptools import find_packages, setup

setup(
    name="protobox-ai",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "protobox=protobox.admin_cli:run",
            "protobox-server=protobox.cli:main",
        ],
    },
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0.0",
        "loguru>=0.7.0",
        "aiohttp>=3.8.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.20.0",
        "websockets>=11.0.0",
        "tenacity>=8.0.0",
        "certifi>=2023.0.0",
        "pyyaml>=6.0.0",
        "click>=8.0.0",
        "motor>=3.3.0",
        "pymongo>=4.5.0",
        "cryptography>=41.0.0",
        "pyjwt>=2.8.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "requests>=2.28.0",
        "rich>=13.0.0",
        "openai>=1.0.0",
        # "openai-agents-python>=0.1.0",  # Not a real package, using fastmcp instead
        "sse-starlette>=1.6.0",
        "fastmcp>=2.0.0",
    ],
)
