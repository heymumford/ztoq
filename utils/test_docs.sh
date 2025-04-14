#!/bin/bash

# Run tests with documentation generation
echo "Running tests with documentation generation..."
python build.py test --with-docs

# Check if documentation was generated
if [ -d "docs/sphinx/build/html" ]; then
    echo "Documentation generated successfully!"
    echo "You can view the documentation by running:"
    echo "python -m http.server 8000 --directory docs/sphinx/build/html"
else
    echo "Documentation generation failed."
    exit 1
fi

# Optionally serve the documentation
if [ "$1" == "--serve" ]; then
    echo "Serving documentation at http://localhost:8000"
    python -m http.server 8000 --directory docs/sphinx/build/html
fi
