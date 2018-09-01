from setuptools import setup, find_packages

setup(
    name="youtube de locke",
    version="1.0.0",
    packages=find_packages(),

    install_requires=[
    	'gevent_websocket',
    	'gunicorn[gevent]',
    	'flask>=1.0.2',
    	'flask_login>=0.4.1',
    	'marshmallow_sqlalchemy>=0.14.1',
    	'flask_marshmallow>=0.9.0',
    	'flask_socketio>=3.0.1',
    	'flask_sqlalchemy>=2.3.2',
    	'statistics',
    ],

    author="Jacob Courtemarche",
    author_email="jacob.courtemarche@gmail.com",
    description="Website built on Flask that synchronizes Youtube videos using websockets",
    license="MIT",
    keywords="flask websockets youtube synchronize",
    url="https://github.com/jtcourtemarche/youtube-de-locke",
    project_urls={
        "Documentation": "https://github.com/jtcourtemarche/youtube-de-locke/blob/master/README.md",
        "Source Code": "https://github.com/jtcourtemarche/youtube-de-locke",
    }
)