# ARIA Android + Laptop Setup

## Requirements

- Laptop with Python 3.10+ and Ollama
- Android Studio
- Android phone with Android 8.0 or newer
- Laptop and phone on the same Wi-Fi/LAN for this milestone

The current project uses AGP 9.4.0, Kotlin 2.2.10, compileSdk 37 and Compose BOM 2026.09.00.

## ایران: Mirror

For dependency/download problems caused by network restrictions, keep Liara Mirrors as an available fallback/reference:

https://liara.ir/mirrors/

A mirror does not guarantee that every dependency or service will be available. Use it only when the required artifact is legally and officially mirrored.

## Laptop

From the repository root:

    cd server
    pip install -r requirements.txt
    python aria_server.py

The server prints a local URL and a six-digit Android pairing code.

Do not publish aria_state.json. It is ignored by Git.

## Android Studio

Open the android folder as an existing Android Studio project.

Use JDK 17 for the Gradle toolchain.

Build and install the app on the phone.

## Pairing

1. Enter the laptop URL shown by the Python server.
2. Enter the six-digit pairing code.
3. Press اتصال.
4. Send a Persian message.

The server creates a device token for this phone. The phone stores the token locally.

## What works

- Laptop hosts the ARIA API.
- Android pairs as a trusted device.
- Android sends a prompt to the laptop.
- Laptop sends the prompt to local Qwen through Ollama.
- ARIA returns the response to Android.
- Android reads the response using Text-to-Speech.
- The server can report Ollama and internet status.

## Current limit

This first milestone needs a network path between phone and laptop. If the internet goes down while the phone and laptop remain on the same LAN, local chat can continue. If there is no path between the devices, Android cannot reach the laptop.

The next milestone adds permissions and structured memory.
