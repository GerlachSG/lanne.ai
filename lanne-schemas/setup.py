from setuptools import setup, find_packages

setup(
    name="lanne-schemas",
    version="0.1.0",
    description="Shared Pydantic models for Lanne AI microservices",
    author="Lanne AI Team",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
    ],
    python_requires=">=3.9",  # Alterado para suportar Python 3.9+
)