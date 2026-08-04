# This is the Python image it needs to run
FROM python:3.12-slim

# Set the working directory inside the container
# All subsequent commands will run from /app
# Equivalent to cd /app
WORKDIR /app

# Install linux level packages required by Python libraries
# gcc, g++: required for compiling some Python packages during pip install
# libgomp1: requied by LightGBM and XGBoost in this implementation
# rm -rf /var/lib/apt/lists/* : removes temporary files to make the image size smaller
RUN apt-get update && \
apt-get install -y gcc g++ libgomp1 && \
rm -rf /var/lib/apt/lists/*

# Install all the requirements
COPY requirements.txt .

# no-cache-dir avoid storing package cache
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# This is the default command that gets executed when the container starts
#  python main.py
CMD ["python", "main.py"]
