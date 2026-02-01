#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для скачивания статических файлов"""
import os
import sys

# Force output to be visible
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

try:
    import requests
except ImportError:
    print("Installing requests...", flush=True)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

def download_file(url, path):
    """Скачивает файл по URL и сохраняет в path"""
    try:
        filename = os.path.basename(path)
        print(f"Downloading {filename}...", flush=True)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(path, 'wb') as f:
            f.write(response.content)
        # Verify file was written
        if not os.path.exists(path):
            print(f"  ERROR: File {path} was not created!", flush=True)
            return False
        size = os.path.getsize(path)
        if size == 0:
            print(f"  ERROR: File {path} is empty!", flush=True)
            return False
        print(f"  ✓ Saved: {size:,} bytes", flush=True)
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

# Список файлов для скачивания
files = [
    ("https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css", "static/css/bootstrap.min.css"),
    ("https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js", "static/js/bootstrap.bundle.min.js"),
    ("https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.min.js", "static/js/vue.min.js"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css", "static/css/font-awesome.min.css"),
    ("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css", "static/css/bootstrap-icons.css"),
    # Font Awesome webfonts
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2", "static/webfonts/fa-solid-900.woff2"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.ttf", "static/webfonts/fa-solid-900.ttf"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2", "static/webfonts/fa-regular-400.woff2"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.ttf", "static/webfonts/fa-regular-400.ttf"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2", "static/webfonts/fa-brands-400.woff2"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.ttf", "static/webfonts/fa-brands-400.ttf"),
]

print("Downloading static files...\n")
success = 0
for url, path in files:
    if download_file(url, path):
        success += 1
        # Verify file was created
        if os.path.exists(path) and os.path.getsize(path) > 0:
            pass  # File is good
        else:
            print(f"  WARNING: File {path} was not created properly!")
            success -= 1

print(f"\nDownloaded {success}/{len(files)} files")

# Final verification
print("\nVerifying downloaded files:")
all_ok = True
for url, path in files:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✓ {os.path.basename(path)}: {size:,} bytes")
    else:
        print(f"  ✗ {os.path.basename(path)}: NOT FOUND")
        all_ok = False

if not all_ok or success < len(files):
    print("\nERROR: Some files failed to download. Please check your internet connection.")
    sys.exit(1)
else:
    print("\n✓ All files downloaded successfully!")

