from setuptools import setup, find_packages

setup(
    name="aidm",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'python-dotenv',
        'langchain_openai',
        'langchain_core',
        'langgraph',
    ],
) 