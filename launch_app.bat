@echo off
title Student Helper AI Assistant
start /b python server.py
timeout /t 2 /nobreak >nul
start msedge --app=http://127.0.0.1:5000