#!/bin/bash
rm -rf build lambda.zip
pip install -r backend/requirements-lambda.txt --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all: --target build/
rsync -av backend/ build/backend/ --exclude tests --exclude seed.py --exclude test_api.py --exclude __pycache__ --exclude .env --exclude .venv
cd ..
echo "Lambda zip size:"
du -h lambda.zip