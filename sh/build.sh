#!/bin/bash


# Verifica se a pasta build existe
if [ -d "build" ]; then
    # Remove a pasta build e seu conteúdo recursivamente
    rm -r build
    echo "Pasta build removida com sucesso."
fi

# Caso nenhuma das pastas exista
if [ ! -d "build" ]; then
    echo "Pasta build foi removida."
fi
