@echo off
rem Abre as 3 instancias do site e o balanceador, cada um na sua janela.
rem Uso: iniciar.bat                  (round robin)
rem      iniciar.bat menos_conexoes
cd /d "%~dp0"
start "Servidor 8001" python servidor.py 8001 0.05
start "Servidor 8002" python servidor.py 8002 0.05
start "Servidor 8003 (mais lento)" python servidor.py 8003 0.2
timeout /t 1 >nul
start "Balanceador" python balanceador.py %1
