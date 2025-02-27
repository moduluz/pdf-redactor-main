import sys
import os
from pathlib import Path
import logging

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('flask_app.log')
    ]
)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, render_template, send_file, flash, redirect, url_for, session
# Import directly from the local pdf_redactor module
from pdf_redactor import PDFRedactor, RedactionConfig

# Create necessary directories if they don't exist
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
REDACTED_DIR = os.path.join(os.path.dirname(__file__), 'redacted')

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REDACTED_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Set a secret key for flash messages and sessions

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/redact', methods=['POST'])
def redact():
    try:
        # Check if a file was uploaded
        if 'pdf_file' not in request.files:
            logger.error("No file part in request")
            flash('No file part', 'error')
            return redirect(url_for('index'))
        
        pdf_file = request.files['pdf_file']
        logger.debug(f"Received file: {pdf_file.filename}")
        
        # Check if the file is selected
        if pdf_file.filename == '':
            logger.error("No file selected")
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        # Check if the file is a PDF
        if not pdf_file.filename.lower().endswith('.pdf'):
            logger.error(f"Invalid file type: {pdf_file.filename}")
            flash('Only PDF files are allowed', 'error')
            return redirect(url_for('index'))
        
        # Create file paths
        input_path = os.path.join(UPLOAD_DIR, pdf_file.filename)
        output_filename = 'redacted_' + pdf_file.filename
        output_path = os.path.join(REDACTED_DIR, output_filename)
        
        logger.info(f"Saving uploaded file to: {input_path}")
        pdf_file.save(input_path)
        
        if not os.path.exists(input_path):
            logger.error(f"Failed to save uploaded file: {input_path}")
            flash('Failed to save uploaded file', 'error')
            return redirect(url_for('index'))
        
        logger.info("Creating redaction configuration")
        # Log redaction options
        redaction_options = {
            'redact_phone': request.form.get('redact_phone') == 'on',
            'redact_email': request.form.get('redact_email') == 'on',
            'redact_iban': request.form.get('redact_iban') == 'on',
            'redact_cc': request.form.get('redact_cc') == 'on',
            'redact_cvv': request.form.get('redact_cvv') == 'on',
            'redact_cc_expiration': request.form.get('redact_cc_expiration') == 'on',
            'redact_bic': request.form.get('redact_bic') == 'on',
            'redact_bic_label': request.form.get('redact_bic_label') == 'on',
            'redact_images': request.form.get('redact_images') == 'on',
            'preserve_headings': request.form.get('preserve_headings') == 'on',
            'redact_aadhaar': request.form.get('redact_aadhaar') == 'on',
            'redact_pan': request.form.get('redact_pan') == 'on',
            'custom_mask': request.form.get('custom_mask'),
            'report_only': request.form.get('report_only') == 'on',
            'verify': request.form.get('verify') == 'on',
            'use_blur': request.form.get('use_blur') == 'on',
            'color': request.form.get('color', 'black'),
            'language': request.form.get('language', 'auto')
        }
        logger.debug(f"Redaction options: {redaction_options}")
        
        # Create a redaction configuration
        config = RedactionConfig(
            redact_phone=redaction_options['redact_phone'],
            redact_email=redaction_options['redact_email'],
            redact_iban=redaction_options['redact_iban'],
            redact_cc=redaction_options['redact_cc'],
            redact_cvv=redaction_options['redact_cvv'],
            redact_cc_expiration=redaction_options['redact_cc_expiration'],
            redact_bic=redaction_options['redact_bic'],
            redact_bic_label=redaction_options['redact_bic_label'],
            redact_images=redaction_options['redact_images'],
            preserve_headings=redaction_options['preserve_headings'],
            redact_aadhaar=redaction_options['redact_aadhaar'],
            redact_pan=redaction_options['redact_pan'],
            custom_mask=redaction_options['custom_mask'],
            input_pdf=input_path,
            output_pdf=output_path,
            report_only=redaction_options['report_only'],
            verify=redaction_options['verify'],
            use_blur=redaction_options['use_blur'],
            color=redaction_options['color'],
            language=redaction_options['language']
        )
        
        logger.info("Initializing PDFRedactor")
        redactor = PDFRedactor(config)
        
        logger.info("Starting redaction process")
        try:
            redactor.redact_document()
            logger.info("Redaction process completed")
        except Exception as e:
            logger.exception("Error during redaction process")
            raise
        
        # Check if the output file exists and has content
        if not os.path.exists(output_path):
            logger.error(f"Output file not created: {output_path}")
            flash('Redaction failed: Output file not created', 'error')
            return redirect(url_for('index'))
            
        if os.path.getsize(output_path) == 0:
            logger.error(f"Output file is empty: {output_path}")
            flash('Redaction failed: Output file is empty', 'error')
            return redirect(url_for('index'))
        
        # Store the output filename in the session for download
        session['output_filename'] = output_filename
        
        logger.info("Redaction completed successfully")
        flash('PDF successfully redacted!', 'success')
        return redirect(url_for('download'))
    
    except Exception as e:
        logger.exception("Redaction failed with error")
        flash(f'Redaction failed: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        # Clean up the uploaded file
        try:
            if 'input_path' in locals() and os.path.exists(input_path):
                os.remove(input_path)
                logger.info(f"Cleaned up uploaded file: {input_path}")
        except Exception as e:
            logger.error(f"Failed to clean up uploaded file: {e}")

@app.route('/download', methods=['GET'])
def download():
    try:
        # Check if the output filename is in the session
        if 'output_filename' not in session:
            logger.error("No output filename in session")
            flash('No redacted file available', 'error')
            return redirect(url_for('index'))
        
        output_filename = session['output_filename']
        output_path = os.path.join(REDACTED_DIR, output_filename)
        
        # Check if the file exists
        if not os.path.exists(output_path):
            logger.error(f"Redacted file not found: {output_path}")
            flash('Redacted file not found', 'error')
            return redirect(url_for('index'))
        
        logger.info(f"Sending redacted file: {output_path}")
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        logger.exception("Download failed")
        flash(f'Download failed: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        # Clean up the redacted file after download
        try:
            if 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
                logger.info(f"Cleaned up redacted file: {output_path}")
        except Exception as e:
            logger.error(f"Failed to clean up redacted file: {e}")

@app.after_request
def add_header(response):
    """
    Add headers to prevent browser caching
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True) 