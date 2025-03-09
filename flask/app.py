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
            flash('Please select a PDF file to redact', 'error')
            return redirect(url_for('index'))
        
        pdf_file = request.files['pdf_file']
        logger.debug(f"Received file: {pdf_file.filename}")
        
        # Check if the file is selected
        if pdf_file.filename == '':
            logger.error("No file selected")
            flash('Please select a PDF file to redact', 'error')
            return redirect(url_for('index'))
        
        # Check if the file is a PDF
        if not pdf_file.filename.lower().endswith('.pdf'):
            logger.error(f"Invalid file type: {pdf_file.filename}")
            flash('Only PDF files are allowed', 'error')
            return redirect(url_for('index'))
        
        # Check file size (limit to 50MB)
        if len(pdf_file.read()) > 50 * 1024 * 1024:  # 50MB in bytes
            logger.error("File too large")
            flash('File size must be less than 50MB', 'error')
            return redirect(url_for('index'))
        pdf_file.seek(0)  # Reset file pointer after reading
        
        # Create file paths with secure filename
        from werkzeug.utils import secure_filename
        secure_fname = secure_filename(pdf_file.filename)
        input_path = os.path.join(UPLOAD_DIR, secure_fname)
        output_filename = 'redacted_' + secure_fname
        output_path = os.path.join(REDACTED_DIR, output_filename)
        
        logger.info(f"Saving uploaded file to: {input_path}")
        pdf_file.save(input_path)
        
        if not os.path.exists(input_path):
            logger.error(f"Failed to save uploaded file: {input_path}")
            flash('Failed to save uploaded file', 'error')
            return redirect(url_for('index'))
        
        logger.info("Creating redaction configuration")
        # Get form data with proper boolean conversion and validation
        def get_bool_param(param_name):
            return request.form.get(param_name, 'off') == 'on'
        
        # Validate color selection
        color = request.form.get('color', 'black')
        valid_colors = ['black', 'white', 'red', 'green', 'blue']
        if color not in valid_colors:
            color = 'black'  # Default to black if invalid
        
        # Validate language selection
        language = request.form.get('language', 'auto')
        valid_languages = ['auto', 'en', 'fr', 'de', 'es', 'it', 'pt', 'nl', 'hi', 'zh', 'ja', 'ko', 'ar', 'ru']
        if language not in valid_languages:
            language = 'auto'  # Default to auto if invalid
        
        # Log redaction options
        redaction_options = {
            'redact_phone': get_bool_param('redact_phone'),
            'redact_email': get_bool_param('redact_email'),
            'redact_iban': get_bool_param('redact_iban'),
            'redact_cc': get_bool_param('redact_cc'),
            'redact_cvv': get_bool_param('redact_cvv'),
            'redact_cc_expiration': get_bool_param('redact_cc_expiration'),
            'redact_bic': get_bool_param('redact_bic'),
            'redact_bic_label': get_bool_param('redact_bic_label'),
            'redact_images': get_bool_param('redact_images'),
            'preserve_headings': get_bool_param('preserve_headings'),
            'redact_aadhaar': get_bool_param('redact_aadhaar'),
            'redact_pan': get_bool_param('redact_pan'),
            'custom_mask': request.form.get('custom_mask', ''),
            'report_only': get_bool_param('report_only'),
            'verify': get_bool_param('verify'),
            'use_blur': get_bool_param('use_blur'),
            'color': color,
            'language': language
        }
        
        logger.debug(f"Redaction options: {redaction_options}")
        
        # Validate that at least one redaction option is selected
        redaction_types = [
            'redact_phone', 'redact_email', 'redact_iban', 'redact_cc',
            'redact_cvv', 'redact_cc_expiration', 'redact_bic',
            'redact_aadhaar', 'redact_pan'
        ]
        
        if not any(redaction_options[opt] for opt in redaction_types):
            logger.error("No redaction options selected")
            flash('Please select at least one type of information to redact', 'error')
            return redirect(url_for('index'))
        
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
            
            # Check if the output file exists and has content
            if not os.path.exists(output_path):
                raise Exception("Output file not created")
                
            if os.path.getsize(output_path) == 0:
                raise Exception("Output file is empty")
            
            # Store the output filename in the session for download
            session['output_filename'] = output_filename
            
            # Generate success message with details
            success_msg = "PDF successfully redacted! "
            if redactor.redaction_stats:
                found_items = [f"{count} {item.lower()}" for item, count in redactor.redaction_stats.items() if count > 0]
                if found_items:
                    success_msg += f"Found and redacted: {', '.join(found_items)}."
            
            logger.info(success_msg)
            flash(success_msg, 'success')
            return redirect(url_for('download'))
            
        except Exception as e:
            logger.exception("Redaction process failed")
            error_msg = str(e)
            if "Permission denied" in error_msg:
                error_msg = "Cannot access the PDF file. Make sure it's not open in another program."
            elif "not a PDF file" in error_msg:
                error_msg = "The file appears to be corrupted or is not a valid PDF."
            flash(f'Redaction failed: {error_msg}', 'error')
            return redirect(url_for('index'))
            
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
            flash('No redacted file available for download', 'error')
            return redirect(url_for('index'))
        
        output_filename = session['output_filename']
        output_path = os.path.join(REDACTED_DIR, output_filename)
        
        # Check if the file exists
        if not os.path.exists(output_path):
            logger.error(f"Redacted file not found: {output_path}")
            flash('The redacted file is no longer available', 'error')
            return redirect(url_for('index'))
        
        # Check if the file is empty
        if os.path.getsize(output_path) == 0:
            logger.error(f"Redacted file is empty: {output_path}")
            flash('The redacted file is empty or corrupted', 'error')
            return redirect(url_for('index'))
        
        logger.info(f"Sending redacted file: {output_path}")
        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/pdf'
        )
        
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
                # Clear the session
                session.pop('output_filename', None)
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
