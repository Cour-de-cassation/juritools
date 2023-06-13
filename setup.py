from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as file:
    requirements = file.read().split("\n")

setup(
    name="juritools",
    version="0.11.1",
    description="Librairie permettant la pseudonymisation des décisions de justice",
    url="https://github.com/Cour-de-cassation/nlp-juritools",
    license="MIT License",
    author="Open Justice, Cour de Cassation",
    author_email="amaury.fouret@justice.fr",
    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,
    package_data={
        "": [
            "postprocessing/data/*.pkl",
            "postprocessing/data/*.txt",
            "postprocessing/data/*.csv",
        ]
    },
    zip_safe=False,
    python_requires=">=3.9",
)
