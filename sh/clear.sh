#!/bin/bash

# Verifica se a pasta exe existe
if [ -d "exe" ]; then
    # Remove a pasta exe e seu conteúdo recursivamente
    rm -r exe
    echo "Pasta exe removida com sucesso."
fi

# Verifica se a pasta build existe
if [ -d "build" ]; then
    # Remove a pasta build e seu conteúdo recursivamente
    rm -r build
    echo "Pasta build removida com sucesso."
fi

# Caso nenhuma das pastas exista
if [ ! -d "exe" ] && [ ! -d "build" ]; then
    echo "As pastas exe e build não existem."
fi
