#!/usr/bin/env bash
set -o errexit

# Verificar versión de Python (debería ser 3.11.9)
python --version

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Comandos Django
python manage.py collectstatic --noinput
python manage.py migrate