import subprocess

subprocess.run(['pyinstaller', '--onedir', 'main.py', '--clean'])
