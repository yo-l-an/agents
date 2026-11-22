@echo off
rem Double-click to watch the Gemini workers live. Close this window to stop the viewer.
title Gemini workers viewer
py -3 "%~dp0viewer.py" %*
if errorlevel 1 pause
