# Setup Guide

## Prerequisites
- Python 3.11+
- pip
- Java 11+ (for WireMock standalone JAR)
- WireMock JAR available in C:\wiremock

## Installation
1. Open terminal in api-validator directory.
2. Create virtual environment:
   - py -3.11 -m venv .venv
3. Activate environment:
   - .venv\Scripts\activate
4. Install dependencies:
   - pip install -r requirements.txt

## WireMock Startup Example
- java -jar C:\wiremock\wiremock-standalone.jar --port 9090 --root-dir wiremock

## Configuration
Edit config.yaml and update:
- swagger_mhtml_path
- legacy_base_url
- new_base_url
- auth fields
- timeout/retry
- ignored_fields
