@echo off
REM Move output files to output newsletter folder

if not exist "output newsletter" mkdir "output newsletter"

REM Move JSON files
move arxiv_*.json "output newsletter\" 2>nul
move newsletter_*.html "output newsletter\" 2>nul
move *.md "output newsletter\" 2>nul

echo Output files moved to 'output newsletter' folder
dir "output newsletter"
pause
