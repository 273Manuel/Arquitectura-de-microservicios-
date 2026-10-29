#!/usr/bin/env bash
# Instala dependencias y compila el frontend (usar como "Build Command").
set -e
python3 -m pip install -r requirements.txt
npm ci
npm run build
