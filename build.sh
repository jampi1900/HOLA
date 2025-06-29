#!/usr/bin/env bash
set -o errexit

# Instalar dependencias (ahora sin aspiref)
pip install -r requirements.txt

# Comandos Django
python manage.py collectstatic --noinput
python manage.py migrate