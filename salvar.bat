@echo off
set /p resposta=Digite 'S' para continuar: 

if /I "%resposta%"=="S" (
    git add .
    git commit -m "Atualização"
    git push
)