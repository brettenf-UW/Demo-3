#!/bin/bash

# Source the environment variables
if [ -f .secrets/.env ]; then
  export $(grep -v '^#' .secrets/.env | xargs)
else
  echo "Error: .secrets/.env file not found"
  exit 1
fi

# Generate Gurobi license file
echo "Generating Gurobi license file..."
envsubst < .secrets/gurobi.lic.template > gurobi.lic
chmod 600 gurobi.lic

echo "Credentials setup complete!"