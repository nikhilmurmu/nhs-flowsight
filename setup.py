from setuptools import setup, find_packages

setup(
    name='nhs-flowsight',
    version='0.1.0',
    packages=[
        'app',
        'app.analysis',
        'app.forecast',
        'app.ingestion',
        'app.dashboard',
        'app.api',
        'app.reports',
    ],
    include_package_data=True,
)
