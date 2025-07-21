#!/usr/bin/env python3
"""
BioMathForge setup.py
Alternative to pyproject.toml for backward compatibility
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    here = os.path.abspath(os.path.dirname(__file__))
    readme_path = os.path.join(here, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Integrated biochemical reaction network generation and pathway analysis toolkit"

setup(
    name="biomathforge",
    version="0.1.0",
    description="Integrated biochemical reaction network generation and pathway analysis toolkit",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Masato Tsutsui",
    author_email="masato.tsutsui@protein.osaka-u.ac.jp",
    url="",
    
    # Package discovery
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Python version requirement
    python_requires=">=3.10",
    
    # Core dependencies
    install_requires=[
        # Core LangGraph and LangChain ecosystem
        "langgraph>=0.2.55",
        "langchain-community>=0.3.9", 
        "langchain-openai>=0.3.7",
        "langchain-anthropic>=0.3.15",
        "langchain-tavily",
        "langsmith>=0.3.37",
        
        # AI/LLM providers
        "openai>=1.61.0",
        "langchain-deepseek>=0.1.2",
        "langchain-groq>=0.2.4",
        "langchain-google-vertexai>=2.0.25",
        "langchain-google-genai>=2.1.5",
        
        # Search and web scraping
        "tavily-python>=0.5.0",
        "duckduckgo-search>=3.0.0",
        "exa-py>=1.8.8",
        "beautifulsoup4>=4.13.3",
        "requests>=2.32.3",
        "httpx>=0.24.0",
        "markdownify>=0.11.6",
        
        # Scientific computing and data analysis
        "pandas>=2.2.1",
        "numpy>=1.26.3",
        "networkx>=3.2.1",
        "tqdm>=4.66.2",
        
        # Configuration and utilities
        "python-dotenv>=1.0.1",
        "pyyaml>=6.0.1",
        "rich>=13.0.0",
        
        # Data formats and parsing
        "pydantic>=2.8.0",
        "xmltodict>=0.14.2",
        "pymupdf>=1.25.3",
        
        # Testing (included in main dependencies for CI/CD)
        "pytest>=8.0.0",
        
        # CLI support
        "langgraph-cli[inmem]>=0.3.1",
    ],
    
    # Optional dependencies
    extras_require={
        # Development dependencies
        "dev": [
            "mypy>=1.11.1",
            "ruff>=0.6.1", 
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=5.0.0",
            "black>=24.0.0",
            "pre-commit>=3.0.0",
        ],
        
        # Documentation dependencies
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=2.0.0",
            "myst-parser>=3.0.0",
            "sphinx-autodoc-typehints>=2.0.0",
        ],
        
        # Notebook and visualization dependencies
        "notebooks": [
            "jupyter>=1.0.0",
            "ipykernel>=6.29.5",
            "matplotlib>=3.8.0",
            "seaborn>=0.13.0",
            "plotly>=5.17.0",
        ],
        
        # Research paper analysis
        "research": [
            "arxiv>=2.1.3",
            "linkup-sdk>=0.2.3",
        ],
        
        # Cloud storage and databases  
        "cloud": [
            "azure-identity>=1.21.0",
            "azure-search>=1.0.0b2",
            "azure-search-documents>=11.5.2", 
            "supabase>=2.15.3",
        ],
        
        # MCP (Model Context Protocol) support
        "mcp": [
            "langchain-mcp-adapters>=0.1.6",
            "mcp>=1.9.4",
        ],
    },
    
    # Include package data
    package_data={
        "biomathforge": [
            "data/templates/*",
            "config/*", 
            "*.yaml",
            "*.yml", 
            "*.json",
            "*.txt",
            "*.md"
        ],
    },
    include_package_data=True,
    
    # Entry points for command-line scripts
    entry_points={
        "console_scripts": [
            "biomathforge-generate=biomathforge.scripts.generate_network:main",
            "biomathforge-analyze=biomathforge.scripts.analyze_pathway:main", 
            "biomathforge-pipeline=biomathforge.scripts.run_full_pipeline:main",
            "biomathforge-validate=biomathforge.scripts.validate_reactions:main",
        ],
    },
    
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11", 
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Operating System :: OS Independent",
    ],
    
    # Keywords for discoverability
    keywords=[
        "systems biology",
        "biochemistry",
        "reaction networks", 
        "pathway analysis",
        "systems biology",
        "bioinformatics",
        "mathematical modeling",
        "AI",
        "machine learning"
    ],
    
    # # Project URLs
    # project_urls={
    #     "Homepage": "https://github.com/yourusername/biomathforge",
    #     "Documentation": "https://biomathforge.readthedocs.io/",
    #     "Repository": "https://github.com/yourusername/biomathforge.git",
    #     "Bug Tracker": "https://github.com/yourusername/biomathforge/issues",
    #     "Changelog": "https://github.com/yourusername/biomathforge/blob/main/CHANGELOG.md",
    # },
    
    # Zip safety
    zip_safe=False,
)
