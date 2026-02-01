#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для скачивания шрифтов Font Awesome"""
import urllib.request
import os
import sys

os.makedirs("static/webfonts", exist_ok=True)

fonts = [
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2", "static/webfonts/fa-solid-900.woff2"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.ttf", "static/webfonts/fa-solid-900.ttf"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2", "static/webfonts/fa-regular-400.woff2"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.ttf", "static/webfonts/fa-regular-400.ttf"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2", "static/webfonts/fa-brands-400.woff2"),
    ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.ttf", "static/webfonts/fa-brands-400.ttf"),
]

print("Downloading Font Awesome webfonts...\n")
for i, (url, path) in enumerate(fonts, 1):
    try:
        print(f"{i}/{len(fonts)}: {os.path.basename(path)}...", end=" ", flush=True)
        urllib.request.urlretrieve(url, path)
        size = os.path.getsize(path)
        print(f"✓ ({size:,} bytes)")
    except Exception as e:
        print(f"✗ Error: {e}")

print("\nDone!")
print(f"\nVerifying files:")
for url, path in fonts:
    if os.path.exists(path):
        print(f"  ✓ {os.path.basename(path)}")
    else:
        print(f"  ✗ {os.path.basename(path)} - NOT FOUND")

