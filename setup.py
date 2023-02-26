from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='APIGatewayHelper',
   version='1.1.1',
   description='Code for extracting arguments from POST requests to API Gateway and for returning values through '
               'API Gateway',
   long_description=long_description,
   author='Pakkapol Lailert',
   author_email='booklailert@gmail.com',
   packages=['APIGatewayInterface'],
   install_requires=[],
)