from setuptools import setup, find_packages

setup(
    name="aidm",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'flask',
        'python-dotenv',
        'gunicorn>=21.2.0',
        'pyyaml',
        'psycopg2-binary',
        'langsmith',
        'langchain_anthropic',
        'langchain_openai',
        'langchain_community',
        'langchain_core',
        'langgraph',
    ],
) 