# 🛡️ PDF Redactor

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-%23000.svg?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An enterprise-grade, privacy-first tool designed to automatically detect and permanently scrub sensitive Personally Identifiable Information (PII) from your PDF documents. 

Whether you're dealing with legal contracts, financial records, or HR documents, PDF Redactor leverages advanced Natural Language Processing (SpaCy) and Optical Character Recognition (Tesseract) to ensure your data stays secure.

---

## ✨ Key Features

- **🧠 Intelligent PII Detection:** Automatically finds and redacts Phone Numbers, Emails, Credit Cards, CVV, Expiry Dates, IBAN, BIC/SWIFT, Aadhaar, and PAN numbers.
- **📸 Deep Image OCR:** Extracts and redacts sensitive text buried inside embedded images and scanned documents using Tesseract OCR.
- **🎨 Flexible Redaction Styles:** Choose between solid black/colored blocks or a subtle text blur effect to obscure data.
- **🌐 Web & CLI Interfaces:** Comes with a beautiful, user-friendly Flask web dashboard, as well as a powerful command-line interface for batch processing.
- **🛡️ Heading Preservation:** Smartly ignores document headers (e.g., preventing the word "PAN" in a title from being redacted) while securely scrubbing the actual sensitive values.
- **🌍 Multi-Language Support:** Auto-detects 14+ languages to ensure accurate pattern matching across international documents.

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
Ensure you have Python 3.9+ installed. You will also need to install the Tesseract OCR engine on your system:
- **Windows:** Download and install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
- **Linux:** `sudo apt-get install tesseract-ocr libtesseract-dev`
- **Mac:** `brew install tesseract`

### 2. Installation
```bash
git clone https://github.com/moduluz/pdf-redactor-main.git
cd pdf-redactor-main
pip install -r requirements.txt
```

### 3. Run the Web Dashboard
We use `waitress` as a production-grade local server. Simply run:
```bash
python wsgi.py
```
Then visit **http://localhost:5000** in your browser.

## 💻 Command-Line Interface (CLI)

Prefer the terminal? The CLI tool is perfect for automation and batch scripts.

```bash
# Basic usage (output defaults to input_redacted.pdf)
python pdf_redactor.py -i document.pdf

# Redact specific items only (e.g., Emails and Indian IDs)
python pdf_redactor.py -i document.pdf --email --aadhaar --pan

# Redact absolutely everything and generate a detailed JSON report
python pdf_redactor.py -i document.pdf --all --verify
```
*Run `python pdf_redactor.py --help` to see all available flags and options.*

## ☁️ Cloud Deployment (Docker/Render)

This project is fully containerized and ready to be deployed to the cloud (like Render, Railway, or AWS) in minutes.

1. Push this repository to your GitHub.
2. Create a new **Web Service** on [Render.com](https://render.com/).
3. Connect your repository.
4. Set the **Environment/Runtime** to **Docker**.
5. Deploy!

The included `Dockerfile` will automatically handle installing system dependencies (like Tesseract), downloading the heavy ML language models, and starting the Waitress production server on port `8080`.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/moduluz/pdf-redactor-main/issues) if you want to contribute.

## 📝 License

This project is [MIT](LICENSE) licensed.
