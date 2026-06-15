# PDF Redactor

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

PDF Redactor is a utility for automatically detecting and redacting Personally Identifiable Information (PII) from PDF documents. It uses `spaCy` for Named Entity Recognition and `pytesseract` to OCR embedded images, ensuring that sensitive data isn't missed even if it's trapped in a scan.

It supports both a CLI for batch operations and a Flask-based web interface.

## Supported Redactions
- Phone numbers, Email addresses
- Credit card numbers, CVV/CVC, Expiration dates
- IBAN and BIC/SWIFT codes
- Indian Government IDs (Aadhaar & PAN)

## Requirements
- Python 3.9+
- `tesseract-ocr` system package

## Local Installation

1. Install Tesseract on your system:
   - **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr libtesseract-dev`
   - **macOS:** `brew install tesseract`
   - **Windows:** Download the binary from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)

2. Clone and install python dependencies:
```bash
git clone https://github.com/moduluz/pdf-redactor-main.git //jist
cd pdf-redactor-main
pip install -r requirements.txt
```

## Usage

### Web Interface
To run the local web dashboard:
```bash
python wsgi.py
```
The server will bind to `localhost:5000` by default.

### CLI
The script can be used directly from the terminal for automation:

```bash
# Redact specific PII categories
python pdf_redactor.py -i document.pdf --email --aadhaar --pan

# Redact all supported categories and verify output
python pdf_redactor.py -i document.pdf --all --verify

# See all available options
python pdf_redactor.py --help
```

## Docker / Cloud Deployment
A `Dockerfile` is included for straightforward deployment on container platforms like Render or AWS. The image uses `python:3.11-slim` and automatically handles the `tesseract-ocr` dependency.

To deploy on Render:
1. Connect this repository to a new Web Service.
2. Select **Docker** as the Runtime environment.
3. Deploy. Waitress will automatically bind to the `$PORT` environment variable.

## License
MIT
