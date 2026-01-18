"""Setup configuration for Claude Calendar Scheduler."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="claude-meet",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Intelligent meeting scheduler using Claude AI and Google Calendar",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/claude-meet",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Communications :: Conferencing",
    ],
    python_requires=">=3.9",
    install_requires=[
        "anthropic>=0.40.0",
        "google-api-python-client>=2.100.0",
        "google-auth-httplib2>=0.1.1",
        "google-auth-oauthlib>=1.1.0",
        "click>=8.1.7",
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
        "python-dotenv>=1.0.0",
        "mcp>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "claude-meet=claude_meet.cli:main",
            "claude-meet-mcp=claude_meet.mcp_server:main",
        ],
    },
    include_package_data=True,
    keywords="calendar, scheduler, claude, ai, meeting, google-calendar",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/claude-meet/issues",
        "Source": "https://github.com/yourusername/claude-meet",
    },
)
