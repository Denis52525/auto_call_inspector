#!/bin/bash
# Запускаем ollama
ollama serve &

# Ждем 5 секунд, чтобы сервер успел подняться
sleep 5

# Подтягиваем модель
ollama pull qwen2.5:3b

# Держим контейнер активным
wait
