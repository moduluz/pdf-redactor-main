# PDF Redactor

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## Overview

PDF Redactor is a secure tool designed to automatically remove sensitive information from PDF documents. It leverages advanced text recognition, image processing, and natural language techniques to detect and redact data such as phone numbers, email addresses, financial details, and more.

## Features

- **Sensitive Data Detection**: Automatically identifies and redacts phone numbers, emails, credit card details, bank information, and more.
- **OCR for Embedded Images**: Uses Tesseract OCR to extract text from images within PDFs.
- **Customizable Redaction Options**: Supports various redaction techniques including color choices, blur effects, and custom mask text.
- **Web Interface Support**: Provides a Flask-based web app for interactive PDF redaction.
- **CLI Integration**: Command-line usage for automated or batch processing.
- **Multi-language Support**: Auto-detect or manually specify document language for improved redaction accuracy.


## Clone the Repository

```bash
git clone https://github.com/moduluz/pdf-redactor-main.git
cd pdf-redactor-main
```

### Quick Start

Install Dependencies
```bash
pip install -r requirements.txt
```

Command-line Usage
```bash
python pdf_redactor.py input.pdf output.pdf
```

Web Interface
```bash
cd flask
python app.py
```

Then, visit http://127.0.0.1:5000 in your browser.


