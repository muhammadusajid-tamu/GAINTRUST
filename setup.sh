#!/bin/bash

# Update system and install virtual environment package
sudo apt update && sudo apt install python3-venv -y

# Create and activate virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Define an array of required Python libraries
packages=(
    tenacity
    transformers
    argparse-dataclass
    anthropic
    boto3
    openai
    google-generativeai
    overrides
    matplotlib
    accelerate
)

# Loop through the array and install each package
for package in "${packages[@]}"; do
    pip install "$package"
done
