#!/bin/bash

# Create a new conda environment named 'neo4j_dev' with Python 3.9
conda create -n neo4j_dev python=3.9 -y

# Activate the environment
conda activate neo4j_dev

# Core dependencies
pip install neo4j                # Neo4j driver
pip install pandas              # Data manipulation
pip install numpy              # Numerical operations

# Visualization packages
pip install networkx           # Network analysis and visualization
pip install matplotlib        # Basic plotting
pip install plotly            # Interactive visualizations
pip install dash              # Web-based dashboards
pip install graphviz          # Graph visualization

# Data processing and analysis
pip install scipy             # Scientific computing
pip install scikit-learn     # Machine learning tools
pip install python-dotenv    # Environment variable management

# Development tools
pip install jupyter          # Jupyter notebooks
pip install ipython         # Enhanced interactive Python shell
pip install pytest          # Testing framework
pip install black           # Code formatter
pip install pylint         # Code linter
pip install notebook       # Jupyter notebook server

# API development (optional)
pip install fastapi         # Fast API framework
pip install uvicorn        # ASGI server
pip install requests       # HTTP requests

# Documentation
pip install sphinx         # Documentation generator
pip install pdoc3         # API documentation generator

# Print environment information
echo "Neo4j development environment created successfully!"
echo "Installed packages:"
pip list
echo ""
echo "To activate the environment, use: conda activate neo4j_dev"
echo "To deactivate the environment, use: conda deactivate" 