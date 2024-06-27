#!/bin/bash

# Verifica se o arquivo .env.prod existe
if [ -f ".env.prod" ]; then
    # Cria a pasta exe se não existir
    mkdir -p exe/main

    # Copia o arquivo .env.prod para exe/.env
    cp .env.prod exe/main/.env

    echo "Arquivo .env.prod copiado para exe/main/.env com sucesso."
else
    echo "Arquivo .env.prod não encontrado."
    exit 1
fi
