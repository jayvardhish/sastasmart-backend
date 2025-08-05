#!/bin/bash
python -m pip install --upgrade pip
pip install -r requirements.txt
gunicorn main:app --bind 0.0.0.0:$PORT
