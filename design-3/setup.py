import setuptools

setuptools.setup(
    name='pedestrian-detection',
    version='0.1',
    install_requires=[
        'apache-beam[gcp]==2.48.0',
        'torch==2.0.1',
        'torchvision==0.15.2',
        'numpy>=1.22.0',
        'Pillow>=9.0.0',
        'google-cloud-pubsub==2.18.0',
    ],
    packages=setuptools.find_packages(),
)
