#!/usr/bin/env python3

import fitz
import phonenumbers
import os
import argparse
import re
import sys
import json
from datetime import datetime
from PIL import Image
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import spacy
from fuzzywuzzy import process
import io
import pytesseract
from langdetect import detect, DetectorFactory, detect_langs
import cv2


# Make language detection deterministic
DetectorFactory.seed = 0

# Set Tesseract path for Windows
tesseract_installed = True
if sys.platform.startswith('win'):
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\USERNAME\AppData\Local\Tesseract-OCR\tesseract.exe',
        # Add your actual installation path here if different
    ]
    
    # Try to find Tesseract in common installation locations
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"[i] Found Tesseract at: {path}")
            break
    else:
        print("[!] Warning: Tesseract OCR not found. Image-based redaction will not work.")
        print("[!] Please install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
        tesseract_installed = False

@dataclass
class RedactionConfig:
    """Configuration for PDF redaction"""
    redact_phone: bool
    redact_email: bool
    redact_iban: bool
    redact_cc: bool
    redact_cvv: bool
    redact_cc_expiration: bool
    redact_bic: bool
    redact_bic_label: bool
    redact_images: bool
    preserve_headings: bool
    redact_aadhaar: bool  # New option for Aadhaar numbers
    redact_pan: bool      # New option for PAN numbers
    custom_mask: Optional[str]
    input_pdf: str        # Path to input PDF file
    output_pdf: str       # Path to output PDF file
    report_only: bool     # Whether to only generate a report without redacting
    verify: bool          # Whether to verify redaction after processing
    use_blur: bool = False  # Option for blur redaction
    color: str = "black"    # Default color for redactions
    language: str = "auto"  # Default to auto-detect language

class PDFRedactor:
    # Define colors as class attributes
    COLORS: Dict[str, tuple] = {
        "white": fitz.pdfcolor["white"],
        "black": fitz.pdfcolor["black"],
        "red": fitz.pdfcolor["red"],
        "green": fitz.pdfcolor["green"],
        "blue": fitz.pdfcolor["blue"]
    }

    # Common heading and label patterns
    HEADING_PATTERNS = [
        r"^(?:Name|Address|Phone|Email|Contact|Title|Position|Department|Company|Organization|Date|Reference|Subject|Re:|Project|Document|Section|Chapter|Part|Appendix|Attachment|Exhibit|Figure|Table|Form|Page|Number|ID|Identification|Code|Status|Type|Category|Class|Group|Level|Grade|Rank|Rating|Score|Value|Amount|Total|Sum|Balance|Credit|Debit|Payment|Invoice|Receipt|Order|Purchase|Sale|Transaction|Account|Customer|Client|Vendor|Supplier|Partner|Associate|Member|User|Owner|Manager|Director|Officer|Executive|Employee|Staff|Personnel|Team|Unit|Division|Branch|Location|Region|Area|Zone|Territory|Market|Segment|Sector|Industry|Field|Domain|Scope|Range|Limit|Threshold|Minimum|Maximum|Average|Mean|Median|Mode|Standard|Requirement|Specification|Condition|Term|Rule|Policy|Procedure|Process|Method|Technique|Approach|Strategy|Plan|Program|Schedule|Timeline|Deadline|Duration|Period|Interval|Frequency|Rate|Ratio|Proportion|Percentage|Fraction|Factor|Element|Component|Module|Function|Feature|Aspect|Attribute|Property|Quality|Characteristic|Trait|Parameter|Variable|Constant|Formula|Equation|Expression|Statement|Declaration|Definition|Description|Explanation|Interpretation|Analysis|Evaluation|Assessment|Review|Summary|Conclusion|Recommendation|Suggestion|Proposal|Option|Alternative|Choice|Decision|Resolution|Solution|Problem|Issue|Challenge|Obstacle|Barrier|Constraint|Limitation|Restriction|Regulation|Law|Statute|Code|Standard|Guideline|Protocol|Convention|Agreement|Contract|License|Permit|Certificate|Credential|Qualification|Degree|Diploma|Award|Prize|Grant|Scholarship|Fellowship|Membership|Subscription|Registration|Enrollment|Admission|Entry|Exit|Departure|Arrival|Origin|Destination|Source|Target|Goal|Objective|Purpose|Intent|Aim|Mission|Vision|Value|Principle|Belief|Philosophy|Theory|Concept|Idea|Thought|Opinion|View|Perspective|Standpoint|Position|Stance|Attitude|Approach|Method|Technique|Procedure|Process|System|Structure|Framework|Architecture|Design|Layout|Format|Style|Mode|Manner|Way|Means|Mechanism|Device|Tool|Instrument|Equipment|Apparatus|Facility|Installation|Infrastructure|Platform|Environment|Context|Setting|Situation|Circumstance|Condition|State|Status|Phase|Stage|Step|Level|Tier|Layer|Dimension|Aspect|Facet|Side|Part|Portion|Segment|Section|Division|Category|Class|Type|Kind|Sort|Form|Shape|Size|Volume|Capacity|Weight|Mass|Density|Pressure|Temperature|Heat|Energy|Power|Force|Strength|Intensity|Magnitude|Amplitude|Frequency|Wavelength|Spectrum|Range|Scope|Extent|Degree|Grade|Quality|Standard|Criterion|Benchmark|Threshold|Limit|Boundary|Border|Edge|Margin|Perimeter|Circumference|Diameter|Radius|Height|Width|Length|Depth|Distance|Interval|Gap|Space|Area|Surface|Volume|Capacity|Content|Amount|Quantity|Number|Count|Tally|Sum|Total|Aggregate|Whole|Complete|Full|Entire|All|Every|Each|Any|Some|Few|Many|Most|Several|Various|Different|Diverse|Distinct|Unique|Special|Particular|Specific|General|Common|Usual|Normal|Typical|Standard|Regular|Ordinary|Average|Median|Mean|Mode|Range|Spread|Distribution|Variation|Deviation|Difference|Discrepancy|Gap|Disparity|Inequality|Imbalance|Asymmetry|Skew|Bias|Tendency|Trend|Pattern|Sequence|Series|Progression|Regression|Correlation|Causation|Effect|Impact|Influence|Significance|Importance|Relevance|Pertinence|Applicability|Validity|Reliability|Accuracy|Precision|Correctness|Truth|Fact|Reality|Actuality|Existence|Being|Presence|Absence|Void|Empty|Null|Zero|Nothing|None|No|Not|Never|Always|Ever|Sometimes|Occasionally|Rarely|Seldom|Often|Frequently|Usually|Normally|Typically|Generally|Commonly|Regularly|Periodically|Intermittently|Sporadically|Randomly|Arbitrarily|Haphazardly|Systematically|Methodically|Logically|Rationally|Reasonably|Sensibly|Practically|Pragmatically|Realistically|Ideally|Theoretically|Hypothetically|Speculatively|Conjecturally|Presumably|Supposedly|Allegedly|Reportedly|Apparently|Seemingly|Ostensibly|Nominally|Formally|Officially|Legally|Legitimately|Validly|Rightfully|Justifiably|Defensibly|Excusably|Pardonably|Forgivably|Understandably|Comprehensibly|Intelligibly|Clearly|Plainly|Obviously|Evidently|Manifestly|Patently|Unquestionably|Indisputably|Undeniably|Irrefutably|Incontrovertibly|Incontestably|Undoubtedly|Certainly|Surely|Definitely|Absolutely|Positively|Completely|Entirely|Wholly|Fully|Totally|Utterly|Thoroughly|Comprehensively|Exhaustively|Extensively|Broadly|Widely|Vastly|Immensely|Tremendously|Enormously|Hugely|Massively|Substantially|Considerably|Significantly|Markedly|Notably|Remarkably|Strikingly|Outstandingly|Exceptionally|Extraordinarily|Extremely|Intensely|Severely|Acutely|Critically|Gravely|Seriously|Profoundly|Deeply|Greatly|Highly|Very|Quite|Rather|Fairly|Moderately|Somewhat|Slightly|Marginally|Minimally|Barely|Hardly|Scarcely|Almost|Nearly|Approximately|About|Around|Roughly|More or Less|Relatively|Comparatively|Proportionally|Accordingly|Correspondingly|Respectively|Individually|Separately|Independently|Autonomously|Freely|Voluntarily|Willingly|Deliberately|Intentionally|Purposely|Consciously|Knowingly|Wittingly|Unwittingly|Unknowingly|Unconsciously|Unintentionally|Accidentally|Inadvertently|Undeliberately|Mistakenly|Erroneously|Incorrectly|Wrongly|Falsely|Inaccurately|Imprecisely|Approximately|Roughly|About|Around|Near|Close|Adjacent|Neighboring|Bordering|Surrounding|Encompassing|Encircling|Enclosing|Containing|Holding|Keeping|Maintaining|Preserving|Conserving|Protecting|Safeguarding|Securing|Ensuring|Guaranteeing|Warranting|Promising|Pledging|Vowing|Swearing|Affirming|Asserting|Claiming|Stating|Declaring|Announcing|Proclaiming|Pronouncing|Promulgating|Publishing|Issuing|Releasing|Distributing|Disseminating|Spreading|Propagating|Transmitting|Conveying|Communicating|Expressing|Articulating|Formulating|Phrasing|Wording|Verbalizing|Voicing|Uttering|Saying|Telling|Relating|Recounting|Narrating|Describing|Depicting|Portraying|Illustrating|Demonstrating|Showing|Displaying|Exhibiting|Presenting|Representing|Symbolizing|Signifying|Denoting|Connoting|Implying|Suggesting|Indicating|Pointing|Referring|Alluding|Hinting|Insinuating|Intimating|Implying|Suggesting|Indicating|Signaling|Signifying|Denoting|Designating|Specifying|Stipulating|Stating|Declaring|Asserting|Affirming|Maintaining|Contending|Arguing|Reasoning|Thinking|Believing|Supposing|Assuming|Presuming|Postulating|Hypothesizing|Theorizing|Speculating|Conjecturing|Guessing|Estimating|Approximating|Calculating|Computing|Reckoning|Counting|Numbering|Enumerating|Listing|Itemizing|Cataloging|Inventorying|Indexing|Tabulating|Charting|Graphing|Plotting|Mapping|Locating|Positioning|Placing|Situating|Stationing|Establishing|Setting|Fixing|Securing|Fastening|Attaching|Connecting|Joining|Linking|Coupling|Pairing|Matching|Fitting|Suiting|Adapting|Adjusting|Aligning|Orienting|Directing|Aiming|Targeting|Focusing|Concentrating|Centering|Converging|Merging|Combining|Uniting|Integrating|Incorporating|Including|Encompassing|Comprising|Containing|Holding|Keeping|Retaining|Maintaining|Preserving|Conserving|Sustaining|Supporting|Upholding|Bearing|Carrying|Conveying|Transporting|Moving|Shifting|Transferring|Relocating|Displacing|Replacing|Substituting|Exchanging|Swapping|Trading|Bartering|Dealing|Transacting|Negotiating|Bargaining|Haggling|Dickering|Bidding|Offering|Proposing|Suggesting|Recommending|Advising|Counseling|Consulting|Conferring|Deliberating|Discussing|Debating|Arguing|Disputing|Contesting|Challenging|Questioning|Doubting|Suspecting|Mistrusting|Distrusting|Disbelieving|Rejecting|Refusing|Declining|Denying|Negating|Contradicting|Opposing|Resisting|Objecting|Protesting|Complaining|Criticizing|Condemning|Denouncing|Censuring|Reproaching|Rebuking|Reprimanding|Admonishing|Chastising|Castigating|Scolding|Berating|Upbraiding|Lambasting|Blasting|Lashing|Attacking|Assaulting|Assailing|Accosting|Confronting|Challenging|Defying|Daring|Provoking|Inciting|Instigating|Agitating|Stirring|Rousing|Arousing|Exciting|Stimulating|Motivating|Inspiring|Encouraging|Urging|Exhorting|Persuading|Convincing|Influencing|Affecting|Impacting|Impressing|Striking|Hitting|Touching|Reaching|Extending|Stretching|Expanding|Enlarging|Increasing|Growing|Developing|Evolving|Progressing|Advancing|Proceeding|Continuing|Persisting|Enduring|Lasting|Remaining|Staying|Abiding|Dwelling|Residing|Living|Existing|Being)(?:\s*:|\s*-|\s*–|\s*—|\s*\(|\s*\[|\s*\{|\s*\<|\s*\>|\s*\||\s*\/|\s*\\|\s*\+|\s*=|\s*\*|\s*&|\s*\^|\s*%|\s*\$|\s*#|\s*@|\s*!|\s*\?|\s*;|\s*,|\s*\.|\s*\'|\s*\"|\s*\`|\s*\~|\s*\s).*$",  # Common label patterns with various separators
        r"^[IVX]{1,5}\.?\s+.*$",  # Roman numeral headings (I. II. III. etc.)
        r"^[A-Z][a-z]*(:|$)",  # Single capitalized word with optional colon
        r"^[A-Z\s]{2,}(:|$)",  # All caps text with optional colon
        r"(Section|Chapter|Title|Part)\s+\d+",  # Section/Chapter indicators
        r"^\d+\.\s+[A-Z]",  # Numbered headings
        r"^[A-Z][a-z]+\s+\d+",  # Word + number headings (Page 1, Section 2)
    ]

    # Language-specific heading patterns
    LANGUAGE_HEADING_PATTERNS = {
        "en": [
            r"^(?:Name|Address|Phone|Email)(?:\s*:|\s*-|\s*–)",
        ],
        "de": [
            r"^(?:Name|Adresse|Telefon|E-Mail)(?:\s*:|\s*-|\s*–)",
        ],
        "fr": [
            r"^(?:Nom|Adresse|Téléphone|Courriel|Email)(?:\s*:|\s*-|\s*–)",
        ],
        "es": [
            r"^(?:Nombre|Dirección|Teléfono|Correo)(?:\s*:|\s*-|\s*–)",
        ]
    }

    def __init__(self, config):
        """Initialize with a RedactionConfig"""
        self.config = config
        
        # Adjusted color map for readability
        self.color_map = {
            "black": (0, 0, 0),
            "white": (1, 1, 1),
            "red": (1, 0, 0),
            "green": (0, 1, 0),
            "blue": (0, 0, 1)
        }
        
        # Set up redaction stats
        self.redaction_stats = {
            "Phone Numbers": 0,
            "Email Addresses": 0,
            "Credit Card Numbers": 0,
            "CVV/CVC Codes": 0,
            "Card Expiration Dates": 0,
            "BIC/SWIFT Codes": 0,
            "IBAN Numbers": 0,
            "Aadhaar Numbers": 0,  # New category for Indian Aadhaar IDs
            "PAN Numbers": 0,      # New category for Indian PAN IDs
            "Custom Pattern": 0
        }
        
        # Initialize report data
        self.report_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input_file": os.path.basename(config.input_pdf),
            "output_file": os.path.basename(config.output_pdf) if config.output_pdf else None,
            "redaction_summary": {},
            "redacted_items": {},
            "verification_results": {}
        }
        
        self.nlp = spacy.load("en_core_web_sm")  # Load the spaCy model here
        self.detected_languages = {}  # Cache for detected languages
        
    def detect_language(self, text):
        """Detect language of the text using langdetect"""
        try:
            detect_langs = detect_langs(text)
            if detect_langs:
                # Take the most probable language
                return detect_langs[0].lang
        except:
            pass
        # Default to English if detection fails
        return "en"
    
    def get_language_specific_patterns(self, language_code):
        """Get regex patterns specific to a language"""
        patterns = {
            "en": {
                "phone": [
                    r"\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
                    r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b"
                ],
                "name": [r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"],
                "address": [
                    r"\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Plaza|Plz|Terrace|Ter|Way)\b",
                    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b"
                ],
                "email": [r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
                "ssn": [r"\b\d{3}-\d{2}-\d{4}\b", r"\bSSN\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}\b"],
                "credit_card": [
                    r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                    r"\b\d{16}\b",
                    r"\b\d{13}\b",
                    r"\b\d{15}\b"
                ]
            },
            "fr": {
                "phone": [
                    r"\b(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}\b",
                    r"\b0\d[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b"
                ],
                "name": [r"\b[A-ZÀÁÂÄÆÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜ][a-zàáâäæçèéêëìíîïñòóôöùúûü]+\s+[A-ZÀÁÂÄÆÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜ][a-zàáâäæçèéêëìíîïñòóôöùúûü]+\b"],
                "address": [
                    r"\b\d+(?:,|\s+)(?:rue|avenue|boulevard|place|cours|chemin|impasse)\s+[A-ZÀÁÂÄÆÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜ][a-zàáâäæçèéêëìíîïñòóôöùúûü]+(?:\s+[A-ZÀÁÂÄÆÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜ][a-zàáâäæçèéêëìíîïñòóôöùúûü]+)*\b",
                    r"\b\d{5}\s+[A-ZÀÁÂÄÆÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜ][a-zàáâäæçèéêëìíîïñòóôöùúûü]+(?:\s+[A-ZÀÁÂÄÆÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜ][a-zàáâäæçèéêëìíîïñòóôöùúûü]+)*\b"
                ],
                "email": [r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
                "ssn": [r"\b\d\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b"], # French social security number
                "credit_card": [
                    r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                    r"\b\d{16}\b",
                    r"\b\d{13}\b",
                    r"\b\d{15}\b"
                ]
            },
            "es": {
                "phone": [
                    r"\b(?:\+34|0034|34)?[\s-]?[6789]\d{8}\b",
                    r"\b(?:\+34|0034|34)?[\s-]?[6789][\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}\b"
                ],
                "name": [r"\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+\s+(?:[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+\s+)?[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+\b"],
                "address": [
                    r"\b(?:Calle|Avenida|Av\.|Plaza|Paseo|Camino)\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)*,?\s+(?:n[úu]mero|nº|#)?\s*\d+\b",
                    r"\b\d{5}\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)*\b"
                ],
                "email": [r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
                "dni": [r"\b\d{8}[A-Z]\b"],  # Spanish national ID
                "nie": [r"\b[XYZ]\d{7}[A-Z]\b"],  # Foreign resident ID
                "credit_card": [
                    r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                    r"\b\d{16}\b"
                ]
            },
            "de": {
                "phone": [
                    r"\b(?:\+49|0049|0)?[\s-]?[1-9]\d{1,4}[\s-]?\d{4,8}\b",
                    r"\b(?:\+49|0049|0)?[\s-]?[1-9]\d{1,2}[\s-]?\d{2,7}[\s-]?\d{2,8}\b"
                ],
                "name": [r"\b[A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß]+\b"],
                "address": [
                    r"\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|str\.|strasse|platz|weg|allee|gasse)\s+\d+[a-z]?\b",
                    r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b"
                ],
                "email": [r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
                "steuer_id": [r"\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b"],  # German tax ID
                "credit_card": [
                    r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                    r"\b\d{16}\b",
                    r"\b\d{13}\b",
                    r"\b\d{15}\b"
                ]
            },
            "hi": {
                # Indian phone number formats
                "phone": [
                    r"\b(?:\+91[-\s]?)?[6789]\d{9}\b",  # Mobile numbers with/without +91
                    r"\b0\d{2,4}[-\s]?\d{6,8}\b",       # Landline with STD codes
                    r"\b\(\d{3,5}\)\s*\d{6,8}\b",       # Parenthesis format for STD
                    r"\b\+91[-\s]?\d{2,5}[-\s]?\d{5,8}\b"  # International format
                ],
                # Aadhaar number (India's national ID)
                "aadhaar": [
                    r"\b\d{4}\s?\d{4}\s?\d{4}\b",       # Standard 12-digit Aadhaar
                    r"\bआधार(?:\s+संख्या)?[:.\s]+\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"  # Prefixed with "Aadhaar" in Hindi
                ],
                # Indian PAN card pattern (tax ID)
                "pan": [
                    r"\b[A-Z]{5}\d{4}[A-Z]\b",          # Standard PAN format
                    r"\bPAN\s*[:.\s]+[A-Z]{5}\d{4}[A-Z]\b" # With PAN prefix
                ],
                # Indian bank account numbers & IFSC codes
                "bank": [
                    r"\b[A-Z]{4}0\d{6}\b",              # IFSC codes
                    r"\b\d{9,18}\b",                    # Bank account numbers
                    r"\b(?:खाता|अकाउंट)(?:\s+संख्या)?[:.\s]+\d{9,18}\b"  # Account prefixed in Hindi
                ],
                # Regular email pattern works for Hindi as well
                "email": [r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
                # Same credit card patterns
                "credit_card": [
                    r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                    r"\b\d{16}\b",
                    r"\b\d{13}\b",
                    r"\b\d{15}\b"
                ],
                # Indian postal code
                "postal": [
                    r"\b\d{6}\b",                       # 6-digit PIN code
                    r"\b[A-Za-z]+,\s*[A-Za-z]+\s*-\s*\d{6}\b"  # City, State - PIN format
                ]
            }
        }
        
        return patterns.get(language_code, patterns["en"])

    @staticmethod
    def print_logo() -> None:
        """Print ASCII art logo"""
        print(r"""
┌─┐┌─┐┬  ┬┌─┐┌─┐┌─┐
├┤ │  │  │├─┘└─┐├┤ 
└─┘└─┘┴─┘┴┴  └─┘└─┘
        made by moduluz
""")
        print("PDF Redactor - Securely redact sensitive information from PDFs")
        print("------------------------------------------------------------------")
        print("Options:")
        print("  --blur              : Use blur-style redaction (asterisks instead of blocks)")
        print("  --color [color]     : Choose redaction color (black, white, red, green, blue)")
        print("  --no-preserve-headings : Redact all matching text, including headings/labels")
        print("  --verify            : Verify redaction after processing")
        print("  --redact-images     : Redact sensitive information in images using OCR")
        print("  --report-only       : Generate a detailed report without performing redactions")
        print("------------------------------------------------------------------")

    def save_redactions(self, pdf_document: fitz.Document, filepath: Union[str, Path]) -> None:
        """Save redacted PDF to file"""
        if isinstance(filepath, Path):
            filepath = str(filepath)
            
        print(f"\n[i] Saving changes to '{filepath}'")
        try:
            pdf_document.save(filepath)
            print(f"[i] Successfully saved redacted PDF to: {filepath}")
        except Exception as e:
            print(f"[Error] Failed to save redacted PDF: {e}")
            raise

    def load_pdf(self, filepath: Path) -> fitz.Document:
        """Load PDF document"""
        try:
            return fitz.open(filepath)
        except Exception as e:
            print(f"[Error] Failed to load PDF: {e}")
            sys.exit(1)

    def ocr_pdf(self, pdf_document: fitz.Document) -> List[str]:
        """Extract text from PDF pages"""
        return [page.get_text("text") for page in pdf_document]

    def find_matches(self, text_pages: List[str], pattern: str, label: str) -> List[str]:
        """Generic pattern matching function"""
        print(f"\n[i] Searching for {label}...")
        matches = []
        for i, page in enumerate(text_pages):
            page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
            matches.extend(page_matches)
            print(f" |  Found {len(page_matches)} {label}{'' if len(page_matches)==1 else 's'} on Page {i+1}: {', '.join(str(p) for p in page_matches)}")
        return matches

    def is_heading(self, text: str, config: RedactionConfig, language_code: str = "en") -> bool:
        """Check if text is likely a heading or label, using language-specific patterns"""
        # If preserve_headings is disabled, don't treat anything as a heading
        if not config.preserve_headings:
            return False
            
        # Skip very long text - headings are typically short
        if len(text) > 50:
            return False
            
        # ALWAYS redact these sensitive items even if they look like headings
        sensitive_patterns = [
            # Credit card related - Enhanced patterns
            r"CVV\s*:?\s*\d{3,4}",
            r"CVC\s*:?\s*\d{3,4}",
            r"CV2\s*:?\s*\d{3,4}",
            r"Security Code\s*:?\s*\d{3,4}",
            r"CSC\s*:?\s*\d{3,4}",  # Card Security Code
            r"CID\s*:?\s*\d{3,4}",  # Card ID (used by AmEx)
            r"\d{3,4}\s+\((?:CVV|CVC|CSC|CID)\)",
            r"(?:\d{4}[- ]?){3}\d{4}",  # Credit card numbers with separators
            r"\b\d{16}\b",  # Raw 16-digit numbers
            r"\b\d{13}\b",  # Some cards have 13 digits
            r"\b\d{15}\b",  # American Express format (15 digits)
            r"\b4[0-9]{12}(?:[0-9]{3})?\b",  # Visa
            r"\b5[1-5][0-9]{14}\b",  # MasterCard
            r"\b3[47][0-9]{13}\b",  # American Express
            r"\b3(?:0[0-5]|[68][0-9])[0-9]{11}\b",  # Diners Club
            r"\b6(?:011|5[0-9]{2})[0-9]{12}\b",  # Discover
            
            # Other financial identifiers - Enhanced patterns
            r"IBAN\s*:?\s*[A-Z]{2}[0-9]{2}[0-9A-Z]{10,30}",
            r"BIC\s*:?\s*[A-Z0-9]{8,11}",
            r"SWIFT\s*:?\s*[A-Z0-9]{8,11}",
            r"Account\s*(?:Number|No|#)?\s*:?\s*\d+",
            r"Routing\s*(?:Number|No|#)?\s*:?\s*\d+",
            r"Sort\s*Code\s*:?\s*\d{2}[-]?\d{2}[-]?\d{2}",
            
            # Expiration related - Enhanced patterns
            r"Expiry\s*:?\s*\d{1,2}[-/]\d{2,4}",
            r"Expiration\s*:?\s*\d{1,2}[-/]\d{2,4}",
            r"Exp\s*:?\s*\d{1,2}[-/]\d{2,4}",
            r"Valid Thru\s*:?\s*\d{1,2}[-/]\d{2,4}",
            r"Exp\. Date\s*:?\s*\d{1,2}[-/]\d{2,4}",
            r"(?:0[1-9]|1[0-2])[-/](?:[0-9]{2}|2[0-9]{3})",  # MM/YY or MM/YYYY
            
            # Personal identifiers - Enhanced patterns
            r"SSN\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}",
            r"Social Security\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}",
            r"\b\d{3}[-]?\d{2}[-]?\d{4}\b",  # Raw SSN format
            r"Tax ID\s*:?\s*\d{2}[-]?\d{7}",
            r"EIN\s*:?\s*\d{2}[-]?\d{7}",
            r"Passport\s*:?\s*[A-Z0-9]{6,9}",
            r"Driver'?s?\s*License\s*:?\s*[A-Z0-9]{6,12}",
            r"ID\s*(?:Number|No|#)?\s*:?\s*[A-Z0-9]{6,12}",
            
            # Phone numbers - Enhanced patterns
            r"Phone\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"Mobile\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"Cell\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"Telephone\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"Tel\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"\b\+?\d{1,3}[-\.\s]?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}\b",  # Generic international format
            r"\b\d{3}[-\.\s]?\d{3}[-\.\s]?\d{4}\b",  # US format without country code
            
            # Email addresses - Enhanced patterns
            r"Email\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            r"E-mail\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",  # Raw email format
            r"\b[a-zA-Z0-9._%+-]+\s*(?:@|\[at\])\s*[a-zA-Z0-9.-]+\s*(?:\.|\[dot\])\s*[a-zA-Z]{2,}\b",  # Obfuscated email
        ]
        
        # Language-specific sensitive patterns
        language_sensitive_patterns = {
            "fr": [
                r"Téléphone\s*:?\s*(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}",
                r"Portable\s*:?\s*(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}",
                r"Courriel\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                r"E-mail\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                r"Numéro de Sécurité Sociale\s*:?\s*\d\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}",
                r"Carte Bleue\s*:?\s*(?:\d{4}[- ]?){3}\d{4}",
                r"N° CB\s*:?\s*(?:\d{4}[- ]?){3}\d{4}",
                r"Cryptogramme\s*:?\s*\d{3,4}"
            ],
            "es": [
                r"Teléfono\s*:?\s*(?:\+34|0034|34)?[\s-]?[6789]\d{8}",
                r"Móvil\s*:?\s*(?:\+34|0034|34)?[\s-]?[6789]\d{8}",
                r"Correo Electrónico\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                r"E-mail\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                r"DNI\s*:?\s*\d{8}[A-Z]",
                r"NIE\s*:?\s*[XYZ]\d{7}[A-Z]",
                r"Tarjeta de Crédito\s*:?\s*(?:\d{4}[- ]?){3}\d{4}",
                r"Código de Seguridad\s*:?\s*\d{3,4}"
            ],
            "de": [
                r"Telefon\s*:?\s*(?:\+49|0049|0)?[\s-]?[1-9]\d{1,4}[\s-]?\d{4,8}",
                r"Handy\s*:?\s*(?:\+49|0049|0)?[\s-]?[1-9]\d{1,4}[\s-]?\d{4,8}",
                r"E-Mail\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                r"Steuer-ID\s*:?\s*\d{2}\s?\d{3}\s?\d{3}\s?\d{3}",
                r"Kreditkarte\s*:?\s*(?:\d{4}[- ]?){3}\d{4}",
                r"Prüfnummer\s*:?\s*\d{3,4}"
            ]
        }
        
        # Add language-specific sensitive patterns if available
        if language_code in language_sensitive_patterns:
            sensitive_patterns.extend(language_sensitive_patterns[language_code])
        
        # If the text matches any sensitive pattern, it's NOT a heading (should be redacted)
        for pattern in sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
                
        # Special case - handle label-value pairs
        # Try to identify if this is a label with sensitive content
        label_value_match = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*:)\s*(.+)$", text.strip())
        if label_value_match:
            label, value = label_value_match.groups()
            
            # Check if the value part contains sensitive information
            value_tests = [
                # Check for credit card patterns in the value
                lambda v: bool(re.search(r"(?:\d{4}[- ]?){3}\d{4}", v)),
                lambda v: bool(re.search(r"\b\d{13,16}\b", v)),
                # Check for SSN pattern
                lambda v: bool(re.search(r"\d{3}[-]?\d{2}[-]?\d{4}", v)),
                # Check for phone number patterns
                lambda v: bool(re.search(r"(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}", v)),
                # Check for email pattern
                lambda v: bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", v)),
                # Check for date patterns that might be expiration dates
                lambda v: bool(re.search(r"\d{1,2}/\d{2,4}", v)),
                # Check for account numbers
                lambda v: bool(re.search(r"\b\d{8,17}\b", v)),
            ]
            
            # If any test returns True, we should redact this text
            if any(test(value) for test in value_tests):
                return False
                
        # Check against language-specific heading patterns if available
        if language_code in self.LANGUAGE_HEADING_PATTERNS:
            for pattern in self.LANGUAGE_HEADING_PATTERNS[language_code]:
                if re.match(pattern, text.strip()):
                    return True
                    
        # Fall back to default heading patterns
        for pattern in self.HEADING_PATTERNS:
            if re.match(pattern, text.strip()):
                return True
                
        # Check for common label formats (e.g., "Name:", "Email:", etc.)
        if re.match(r"^[A-Z][a-z]+\s*:", text.strip()):
            return True
            
        return False

    def blur_text(self, pdf_document: fitz.Document, matches: List[str], config: RedactionConfig) -> None:
        """Apply blur effect instead of block redaction, with language detection support"""
        if not matches:
            return
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            page_text = page.get_text("text")
            
            # Detect language for this page if needed
            language_code = "en"  # Default
            if config.language == "auto":
                # Check if we've already detected the language for this page content
                if page_text not in self.detected_languages:
                    self.detected_languages[page_text] = self.detect_language(page_text)
                language_code = self.detected_languages[page_text]
            else:
                language_code = config.language
                
            for match in matches:
                # Skip if this is a heading and we're preserving headings
                if self.is_heading(match, config, language_code):
                    print(f" |  Preserving heading/label: {match}")
                    continue
                
                # For labels with sensitive content, try to redact only the content part
                label_match = re.match(r"^([A-Z][a-z]+\s*:)\s*(.+)$", match)
                if config.preserve_headings and label_match:
                    label, content = label_match.groups()
                    # Try to find and redact only the content part
                    content_rects = page.search_for(content)
                    if content_rects:
                        for rect in content_rects:
                            # Create a semi-transparent redaction with asterisks
                            blur_text = '*' * len(content)
                            fill_color = list(self.COLORS[config.color])
                            fill_color.append(0.5)  # Add transparency
                            
                            annot = page.add_redact_annot(
                                quad=rect,
                                text=blur_text,
                                text_color=self.COLORS["black"],
                                fill=fill_color,
                                cross_out=False
                            )
                            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                        continue
                
                # Regular redaction for non-heading content
                rects = page.search_for(match)
                for rect in rects:
                    # Create a semi-transparent redaction with asterisks
                    blur_text = '*' * len(match)
                    fill_color = list(self.COLORS[config.color])
                    fill_color.append(0.5)  # Add transparency
                    
                    annot = page.add_redact_annot(
                        quad=rect,
                        text=blur_text,
                        text_color=self.COLORS["black"],
                        fill=fill_color,
                        cross_out=False
                    )
                    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    def redact_matches(self, pdf_document: fitz.Document, matches: List[str], config: RedactionConfig) -> None:
        """Apply redactions for matched content with language detection support"""
        if not matches:
            return
        
        # If blur redaction is enabled, use blur_text method instead
        if config.use_blur:
            self.blur_text(pdf_document, matches, config)
            return

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            page_text = page.get_text("text")
            
            # Detect language for this page if needed
            language_code = "en"  # Default
            if config.language == "auto":
                # Check if we've already detected the language for this page content
                if page_text not in self.detected_languages:
                    self.detected_languages[page_text] = self.detect_language(page_text)
                language_code = self.detected_languages[page_text]
                if language_code:
                    print(f" |  Detected language for page {page_num+1}: {language_code}")
            else:
                language_code = config.language
                
            for match in matches:
                # Skip if this is a heading and we're preserving headings
                if self.is_heading(match, config, language_code):
                    print(f" |  Preserving heading/label: {match}")
                    continue
                
                # For labels with sensitive content, try to redact only the content part
                label_match = re.match(r"^([A-Z][a-z]+\s*:)\s*(.+)$", match)
                if config.preserve_headings and label_match:
                    label, content = label_match.groups()
                    # Try to find and redact only the content part
                    content_rects = page.search_for(content)
                    if content_rects:
                        for rect in content_rects:
                            page.add_redact_annot(rect, fill=fitz.utils.getColor(config.color))
                            page.apply_redactions()
                        continue
                
                # Regular redaction for non-heading content
                rects = page.search_for(match)
                for rect in rects:
                    page.add_redact_annot(rect, fill=fitz.utils.getColor(config.color))
                    page.apply_redactions()

    def preview_redaction(self, page: fitz.Page, annot: fitz.Annot) -> None:
        """Preview redaction and get user confirmation"""
        zoom = 3
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.show()

        while True:
            user_input = input("[?] Continue with redaction? (Y/n): ").strip().lower()
            if user_input == 'y':
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                break
            elif user_input == 'n':
                print(" |  Redaction aborted.")
                page.delete_annot(annot)
                break
            print("[Error] Invalid input. Please enter 'Y' to continue or 'n' to abort.")

    def redact_images(self, pdf_document: fitz.Document, config: RedactionConfig) -> List[Dict]:
        """Redact sensitive information from images in the PDF"""
        if not tesseract_installed:
            print("\n[Error] Tesseract OCR is not installed. Cannot perform image-based redaction.")
            print("[i] Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
            print("[i] Make sure to check 'Add to PATH' during installation.")
            return []
        
        try:
            import cv2
            import numpy as np
            has_cv2 = True
            # Load face detection cascade
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if face_cascade.empty():
                print("[Warning] Could not load face cascade classifier")
                has_cv2 = False
        except ImportError:
            print("\n[Warning] OpenCV (cv2) not found. Face detection will be limited.")
            has_cv2 = False
        
        print("\n[i] Searching for text and personal images...")
        image_redaction_info = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            try:
                # Get all images on the page
                image_list = page.get_images(full=True)
                if not image_list:
                    continue
                
                print(f" |  Processing {len(image_list)} images on Page {page_num + 1}")
                
                # Get page dimensions
                page_rect = page.rect
                
                # Get all image blocks on the page
                image_blocks = []
                for block in page.get_text("dict")["blocks"]:
                    if block.get("type") == 1:  # Type 1 is image
                        image_blocks.append(block)
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Convert to PIL Image
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        width, height = pil_image.size
                        
                        # Convert to numpy array for OpenCV processing
                        if has_cv2:
                            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                        
                        # Check for faces if OpenCV is available
                        has_face = False
                        if has_cv2:
                            try:
                                # Detect faces with different scale factors for better accuracy
                                scale_factors = [1.1, 1.2, 1.3]
                                min_neighbors_values = [3, 4, 5]
                                
                                for scale_factor in scale_factors:
                                    for min_neighbors in min_neighbors_values:
                                        faces = face_cascade.detectMultiScale(
                                            gray,
                                            scaleFactor=scale_factor,
                                            minNeighbors=min_neighbors,
                                            minSize=(20, 20)
                                        )
                                        if len(faces) > 0:
                                            has_face = True
                                            print(f" |  Found {len(faces)} face(s) in image {img_index+1} on Page {page_num+1}")
                                            break
                                    if has_face:
                                        break
                            except Exception as e:
                                print(f" |  Error during face detection: {e}")
                        
                        # Check image dimensions for potential passport/ID photos
                        aspect_ratio = width / height
                        is_potential_id = (
                            (width <= 800 and height <= 1000) and  # Common passport/ID photo size
                            (0.6 <= aspect_ratio <= 1.0)  # Common passport/ID photo aspect ratio
                        )
                        
                        # Try OCR for text-based sensitive info
                        text = pytesseract.image_to_string(pil_image)
                        
                        # Additional OCR for high-res images
                        if width > 1000 or height > 1000:
                            text_hq = pytesseract.image_to_string(
                                pil_image,
                                config='--oem 1 --psm 3 -c preserve_interword_spaces=1'
                            )
                            text += "\n" + text_hq
                        
                        # Check for sensitive information
                        found_sensitive = False
                        found_types = []
                        
                        # Add face detection result
                        if has_face:
                            found_sensitive = True
                            found_types.append("Face Detected")
                        
                        # Add potential ID photo detection
                        if is_potential_id:
                            found_sensitive = True
                            found_types.append("Potential ID Photo")
                        
                        # Check for phone numbers
                        if config.redact_phone:
                            phone_patterns = [
                                r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                                r"\b\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b"
                            ]
                            for pattern in phone_patterns:
                                if re.search(pattern, text):
                                    found_sensitive = True
                                    found_types.append("Phone Numbers")
                                    break
                        
                        # Check for email addresses
                        if config.redact_email:
                            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                            if re.search(email_pattern, text):
                                found_sensitive = True
                                found_types.append("Email Addresses")
                        
                        if found_sensitive:
                            print(f" |  Found sensitive information in image {img_index+1} on Page {page_num+1}: {', '.join(found_types)}")
                            
                            # Try to find the image block that matches this image
                            image_rect = None
                            if img_index < len(image_blocks):
                                block = image_blocks[img_index]
                                image_rect = fitz.Rect(block["bbox"])
                            
                            # If we found a rectangle, apply redaction
                            if image_rect and image_rect.is_valid and not image_rect.is_empty:
                                try:
                                    # Create redaction annotation
                                    annot = page.add_redact_annot(
                                        image_rect,
                                        text="[REDACTED IMAGE]" if config.use_blur else None,
                                        fill=self.COLORS[config.color]
                                    )
                                    
                                    # Apply the redaction
                                    page.apply_redactions()
                                    
                                    # Record redaction info
                                    image_redaction_info.append({
                                        "page": page_num + 1,
                                        "image_index": img_index + 1,
                                        "types": found_types,
                                        "dimensions": f"{width}x{height}"
                                    })
                                    
                                    print(f" |  Successfully redacted image {img_index+1} on Page {page_num+1}")
                                except Exception as e:
                                    print(f" |  Error applying redaction to image {img_index+1} on Page {page_num+1}: {e}")
                            else:
                                print(f" |  Could not determine location of image {img_index+1} on Page {page_num+1}")
                    
                    except Exception as e:
                        print(f" |  Error processing image {img_index+1} on Page {page_num+1}: {e}")
            
            except Exception as e:
                print(f" |  Error getting images from Page {page_num+1}: {e}")
        
        return image_redaction_info

    def verify_redaction(self, redacted_pdf_path: Path, sensitive_patterns: List[str]) -> bool:
        """Verify that all sensitive information has been properly redacted"""
        print("\n[i] Verifying redaction...")
        doc = self.load_pdf(redacted_pdf_path)
        text_pages = self.ocr_pdf(doc)
        all_text = " ".join(text_pages)
        
        found_sensitive_info = False
        pattern_matches = {}
        
        # Organize patterns into categories for better reporting
        pattern_categories = {
            "Credit Card Numbers": [
                r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                r"\b\d{16}\b",
                r"\b\d{13}\b",
                r"\b\d{15}\b",
                r"\b(?:4\d{12}(?:\d{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b"
            ],
            "CVV/CVC Codes": [
                r"\b(?:cvv|cvc|cvv2|cvc2|security\s+code|card\s+security\s+code|verification\s+code|security\s+number)[:.\s]+(\d{3,4})\b",
                r"\b(\d{3,4})\s*\((?:cvv|cvc|security\s+code)\)",
                r"\b(?:cvv|cvc|security)\s*(?:number|code|verification)?\s*[:.\s]+(\d{3,4})\b"
            ],
            "Expiration Dates": [
                r"\bExpiry\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bExpiration\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bExp\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bValid Thru\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bExp\.\s*Date\s*:?\s*\d{1,2}/\d{2,4}\b"
            ],
            "Phone Numbers": [
                r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
                r"\b\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b",
                r"\b(?:phone|tel|telephone|mobile|cell|contact)[:.\s]+(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
            ],
            "Email Addresses": [
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            ]
        }
        
        page_results = {}
        
        for page_num, page_text in enumerate(text_pages):
            page_results[page_num + 1] = {}
            
            for category, patterns in pattern_categories.items():
                category_matches = []
                for pattern in patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        for match in matches:
                            # Skip if it looks like a year (e.g., 2023)
                            if re.match(r"\b(?:19|20)\d{2}\b", str(match)):
                                continue
                                
                            # Skip if it looks like a page number or section number
                            if re.match(r"\b[1-9]\d{0,3}\b", str(match)):
                                continue
                                
                            category_matches.append(match)
                
                if category_matches:
                    found_sensitive_info = True
                    unique_matches = list(set(category_matches))
                    page_results[page_num + 1][category] = unique_matches
                    
                    # Add to overall pattern matches
                    cat_key = f"{category} (Page {page_num + 1})"
                    pattern_matches[cat_key] = unique_matches
        
        # Also check images if Tesseract is available
        if tesseract_installed:
            print("[i] Checking images for sensitive information...")
            for page_num in range(len(doc)):
                page = doc[page_num]
                images = page.get_images(full=True)
                
                for img_index, img_info in enumerate(images):
                    try:
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        
                        # Try multiple OCR approaches for better accuracy
                        text = pytesseract.image_to_string(pil_image)
                        
                        # Try with better settings for high-res images
                        if pil_image.width > 1000 or pil_image.height > 1000:
                            text_hq = pytesseract.image_to_string(
                                pil_image, 
                                config='--oem 1 --psm 3 -c preserve_interword_spaces=1'
                            )
                            text += "\n" + text_hq
                        
                        if text.strip():
                            for category, patterns in pattern_categories.items():
                                category_matches = []
                                for pattern in patterns:
                                    matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                                    if matches:
                                        category_matches.extend(matches)
                                
                                if category_matches:
                                    found_sensitive_info = True
                                    unique_matches = list(set(category_matches))
                                    cat_key = f"Image-{page_num+1}-{img_index+1}: {category}"
                                    pattern_matches[cat_key] = unique_matches
                                    
                                    # Add to page results for consolidated reporting
                                    if page_num + 1 not in page_results:
                                        page_results[page_num + 1] = {}
                                    
                                    img_cat_key = f"{category} (Image)"
                                    if img_cat_key not in page_results[page_num + 1]:
                                        page_results[page_num + 1][img_cat_key] = []
                                    
                                    page_results[page_num + 1][img_cat_key].extend(unique_matches)
                    except Exception as e:
                        print(f" |  Error checking image {img_index+1} on Page {page_num+1}: {e}")
        
        # Reporting
        if not found_sensitive_info:
            print("\n[SUCCESS] No sensitive information detected in the redacted document.")
            return True
        else:
            print("\n[FAILURE] Redaction verification failed - sensitive information still present:")
            print("=" * 80)
            
            # Organized report by page
            print("DETAILED REPORT BY PAGE:")
            for page_num in sorted(page_results.keys()):
                if page_results[page_num]:
                    print(f"\nPAGE {page_num}:")
                    print("-" * 40)
                    for category, matches in page_results[page_num].items():
                        print(f"  {category}: {len(matches)} match(es)")
                        for i, match in enumerate(matches[:3]):  # Show first 3
                            print(f"    - {match}")
                        if len(matches) > 3:
                            print(f"    ... and {len(matches)-3} more")
            
            print("\n" + "=" * 80)
            print("RECOMMENDATIONS:")
            print("1. Try running the redaction again with --no-preserve-headings flag")
            print("2. Add specific patterns for the types of sensitive data found")
            print("3. Use --verify after redaction to confirm all sensitive data is removed")
            print("4. For stubborn text in images, try --redact-images option")
            print("=" * 80)
            
            return False

    def process_file(self, filepath: Path, config: RedactionConfig) -> None:
        """Process a single PDF file"""
        # Check if file is a text file
        if isinstance(filepath, str):
            filepath = Path(filepath)
            
        if filepath.suffix.lower() == '.txt':
            self.process_text_file(filepath, config)
            return
            
        pdf_document = self.load_pdf(filepath)
        text_pages = self.ocr_pdf(pdf_document)
        
        # Collect all patterns for redaction and later verification
        sensitive_patterns = []
        
        # Track redacted items for reporting
        redacted_items = {}

        # Phone numbers - Improved detection with international formats
        if config.redact_phone:
            phone_patterns = [
                r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}",  # Standard format
                r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",  # US format: 123-456-7890
                r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",  # US format: (123) 456-7890
                r"\b\+\d{1,3}\s?\d{2,3}\s?\d{3,4}\s?\d{3,4}\b",  # International: +XX XX XXXX XXXX
                r"\b\d{5,6}[-.\s]?\d{5,6}\b"  # Some European formats
            ]
            sensitive_patterns.extend(phone_patterns)
            
            # Standard phonenumbers library detection
            phone_matches = []
            for page in text_pages:
                for match in phonenumbers.PhoneNumberMatcher(page, None):
                    phone_matches.append(match.raw_string)
                    
            # Additional regex-based detection
            for pattern in phone_patterns:
                additional_matches = self.find_matches(text_pages, pattern, "Phone Numbers")
                phone_matches.extend(additional_matches)
                
            # Remove duplicates while preserving order
            phone_matches = list(dict.fromkeys(phone_matches))
            self.redact_matches(pdf_document, phone_matches, config)
            
            if phone_matches:
                redacted_items["Phone Numbers"] = phone_matches

        # Email addresses - Enhanced pattern
        if config.redact_email:
            email_patterns = [
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Standard email
                r"[a-zA-Z0-9._%+-]+\s+at\s+[a-zA-Z0-9.-]+\s+dot\s+[a-zA-Z]{2,}",  # "user at domain dot com" format
                r"[a-zA-Z0-9._%+-]+\[at\][a-zA-Z0-9.-]+\[dot\][a-zA-Z]{2,}"  # "user[at]domain[dot]com" format
            ]
            sensitive_patterns.extend(email_patterns)
            
            all_email_matches = []
            for pattern in email_patterns:
                email_matches = self.find_matches(text_pages, pattern, "Email Addresses")
                all_email_matches.extend(email_matches)
                
            self.redact_matches(pdf_document, all_email_matches, config)
            
            if all_email_matches:
                redacted_items["Email Addresses"] = all_email_matches

        # Credit Card Numbers - Enhanced pattern to catch more formats
        if config.redact_cc:
            credit_card_patterns = [
                r"\b(?:\d{4}[- ]?){3}\d{4}\b",  # Standard 16-digit cards with optional separators
                r"\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b",  # Cards with spaces
                r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",  # Cards with hyphens
                r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",  # Raw card numbers by issuer
                r"\b\d{16}\b",  # Raw 16-digit numbers without separators
                r"\b\d{13}\b",  # Some cards have 13 digits (like some Visa)
                r"\b\d{15}\b",  # American Express format (15 digits)
                r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|3(?:0[0-5]|[68]\d)\d{11}|6(?:011|5\d{2})\d{12}|(?:2131|1800|35\d{3})\d{11})\b"  # Card numbers without separators by issuer
            ]
            
            sensitive_patterns.extend(credit_card_patterns)
            credit_card_matches_all = []
            for pattern in credit_card_patterns:
                credit_card_matches = self.find_matches(text_pages, pattern, "Credit Card Numbers")
                credit_card_matches_all.extend(credit_card_matches)
                self.redact_matches(pdf_document, credit_card_matches, config)
                
            if credit_card_matches_all:
                redacted_items["Credit Card Numbers"] = list(set(credit_card_matches_all))

        # CVV/CVC Codes - More comprehensive patterns
        if config.redact_cvv:
            cvv_patterns = [
                r"\bCVV\s*:?\s*\d{3,4}\b",  # CVV: 123
                r"\bCVC\s*:?\s*\d{3,4}\b",  # CVC: 123
                r"\bCV2\s*:?\s*\d{3,4}\b",  # CV2: 123
                r"\bSecurity Code\s*:?\s*\d{3,4}\b",  # Security Code: 123
                r"\b\d{3,4}\s+\(CVV\)\b",  # 123 (CVV)
                r"\b\d{3,4}\s+\(CVC\)\b",  # 123 (CVC)
                r"\b\d{3,4}\s+\(Security Code\)\b",  # 123 (Security Code)
                r"\bCSC\s*:?\s*\d{3,4}\b",  # CSC: 123 (Card Security Code)
                r"\bCID\s*:?\s*\d{3,4}\b",  # CID: 123 (Card Identification Number used by AmEx)
                r"\bCVN\s*:?\s*\d{3,4}\b",  # CVN: 123 (Card Verification Number)
                r"\bCVD\s*:?\s*\d{3,4}\b",  # CVD: 123 (Card Verification Data)
                r"(?<!\d)\d{3,4}(?!\d)"  # Isolated 3-4 digit numbers that might be CVV/CSC
            ]
            
            sensitive_patterns.extend(cvv_patterns)
            cvv_matches_all = []
            for pattern in cvv_patterns:
                cvv_matches = self.find_matches(text_pages, pattern, "CVV/CVC Codes")
                cvv_matches_all.extend(cvv_matches)
                self.redact_matches(pdf_document, cvv_matches, config)
                
            if cvv_matches_all:
                redacted_items["CVV/CVC Codes"] = list(set(cvv_matches_all))
                
        # Card Expiration Dates
        if config.redact_cc_expiration:
            expiry_patterns = [
                r"\bExpiry\s*:?\s*\d{1,2}/\d{2,4}\b",  # Expiry: 05/26
                r"\bExpiration\s*:?\s*\d{1,2}/\d{2,4}\b",  # Expiration: 05/26
                r"\bExp\s*:?\s*\d{1,2}/\d{2,4}\b",  # Exp: 05/26
                r"\bValid Thru\s*:?\s*\d{1,2}/\d{2,4}\b",  # Valid Thru: 05/26
                r"\bExp\. Date\s*:?\s*\d{1,2}/\d{2,4}\b"  # Exp. Date: 05/26
            ]
            
            sensitive_patterns.extend(expiry_patterns)
            expiry_matches_all = []
            for pattern in expiry_patterns:
                expiry_matches = self.find_matches(text_pages, pattern, "Card Expiration Dates")
                expiry_matches_all.extend(expiry_matches)
                self.redact_matches(pdf_document, expiry_matches, config)
                
            if expiry_matches_all:
                redacted_items["Card Expiration Dates"] = list(set(expiry_matches_all))

        # BIC Codes - Improved pattern
        if config.redact_bic:
            bic_pattern = r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"  # Standard BIC/SWIFT format
            sensitive_patterns.append(bic_pattern)
            bic_matches = self.find_matches(text_pages, bic_pattern, "BIC/SWIFT Codes")
            self.redact_matches(pdf_document, bic_matches, config)
            
            # Also look for BIC labels with content
            bic_label_pattern = r"\bBIC\s*:?\s*[A-Z0-9]{8,11}\b"
            sensitive_patterns.append(bic_label_pattern)
            bic_label_matches = self.find_matches(text_pages, bic_label_pattern, "BIC Labels")
            self.redact_matches(pdf_document, bic_label_matches, config)
            
            if bic_matches or bic_label_matches:
                redacted_items["BIC/SWIFT Codes"] = list(set(bic_matches + bic_label_matches))

        # Custom mask
        if config.custom_mask:
            pattern = r'\b' + re.escape(config.custom_mask) + r'\b'
            sensitive_patterns.append(pattern)
            matches = self.find_matches(text_pages, pattern, "Custom Mask matches")
            self.redact_matches(pdf_document, matches, config)
            if matches:
                redacted_items["Custom Mask"] = matches

        # IBAN - Improved pattern
        if config.redact_iban:
            iban_patterns = [
                r'\b[A-Z]{2}[0-9]{2}(?:[ ]?[0-9]{4}){4}(?!(?:[ ]?[0-9]){3})(?:[ ]?[0-9]{1,2})?\b',  # Standard format
                r'\bIBAN\s*:?\s*[A-Z]{2}[0-9]{2}[0-9A-Z]{10,30}\b'  # IBAN with label
            ]
            sensitive_patterns.extend(iban_patterns)
            iban_matches_all = []
            for pattern in iban_patterns:
                ibans = self.find_matches(text_pages, pattern, "IBANs")
                iban_matches_all.extend(ibans)
                self.redact_matches(pdf_document, ibans, config)
                
            if iban_matches_all:
                redacted_items["IBAN Numbers"] = list(set(iban_matches_all))

        # Image redaction tracking
        if config.redact_images:
            image_redaction_info = self.redact_images(pdf_document, config)
            if image_redaction_info:
                redacted_items["Images"] = image_redaction_info

        # Save results
        if isinstance(config.output_pdf, str):
            out_path = config.output_pdf
        else:
            out_path = filepath.parent / f"{filepath.stem}_redacted{filepath.suffix}"
            
        self.save_redactions(pdf_document, out_path)
        
        # Generate redaction report
        self.generate_redaction_report(filepath, out_path, redacted_items)
        
        # Verify redaction if requested
        if config.verify:
            self.verify_redaction(out_path, sensitive_patterns)
            
    def generate_redaction_report(self, input_path: Path, output_path: Path, redacted_items: Dict[str, List[str]]) -> None:
        """Generate a report of what was redacted"""
        # Calculate total items redacted
        total_items = sum(len(items) for items in redacted_items.values())
        
        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input_file": str(input_path),
            "output_file": str(output_path),
            "total_items_redacted": total_items,
            "redacted_items": redacted_items
        }
        
        # Save report to JSON file
        report_path = input_path.parent / f"{input_path.stem}_redaction_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n[i] Redaction report saved to: {report_path}")
        
        # Print summary
        print("\n[REDACTION SUMMARY]")
        print(f"Total items redacted: {total_items}")
        if redacted_items:
            print("By category:")
            for category, items in redacted_items.items():
                print(f"  - {category}: {len(items)} item(s)")

    def scan_and_report(self, filepath: Path, args: argparse.Namespace) -> None:
        """Scan PDF for sensitive information and generate a report without redacting"""
        print(f"\n[i] Scanning file for sensitive information without redacting: {filepath}")
        pdf_document = self.load_pdf(filepath)
        text_pages = self.ocr_pdf(pdf_document)
        
        # Collect sensitivity findings
        findings = {}
        
        # Phone numbers
        if args.phonenumber:
            phone_patterns = [
                r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}",  # Standard format
                r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",  # US format: 123-456-7890
                r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",  # US format: (123) 456-7890
                r"\b\+\d{1,3}\s?\d{2,3}\s?\d{3,4}\s?\d{3,4}\b",  # International: +XX XX XXXX XXXX
                r"\b\d{5,6}[-.\s]?\d{5,6}\b"  # Some European formats
            ]
            
            # Standard phonenumbers library detection
            phone_matches = []
            for page_num, page in enumerate(text_pages):
                for match in phonenumbers.PhoneNumberMatcher(page, None):
                    phone_matches.append({
                        "value": match.raw_string,
                        "page": page_num + 1
                    })
                    
            # Additional regex-based detection
            for pattern in phone_patterns:
                for page_num, page in enumerate(text_pages):
                    page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
                    for match in page_matches:
                        phone_matches.append({
                            "value": match,
                            "page": page_num + 1
                        })
            
            if phone_matches:
                findings["Phone Numbers"] = phone_matches
                print(f" |  Found {len(phone_matches)} phone number(s)")

        # Email addresses
        if args.email:
            email_patterns = [
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Standard email
                r"[a-zA-Z0-9._%+-]+\s+at\s+[a-zA-Z0-9.-]+\s+dot\s+[a-zA-Z]{2,}",  # "user at domain dot com" format
                r"[a-zA-Z0-9._%+-]+\[at\][a-zA-Z0-9.-]+\[dot\][a-zA-Z]{2,}"  # "user[at]domain[dot]com" format
            ]
            
            email_matches = []
            for pattern in email_patterns:
                for page_num, page in enumerate(text_pages):
                    page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
                    for match in page_matches:
                        email_matches.append({
                            "value": match,
                            "page": page_num + 1
                        })
            
            if email_matches:
                findings["Email Addresses"] = email_matches
                print(f" |  Found {len(email_matches)} email address(es)")

        # Credit Card Numbers
        credit_card_patterns = [
            r"\b(?:\d{4}[- ]?){3}\d{4}\b",  # Standard 16-digit cards with optional separators
            r"\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b",  # Cards with spaces
            r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",  # Cards with hyphens
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",  # Raw card numbers by issuer
            r"\b\d{16}\b",  # Raw 16-digit numbers without separators
            r"\b\d{13}\b",  # Some cards have 13 digits (like some Visa)
            r"\b\d{15}\b",  # American Express format (15 digits)
        ]
        
        cc_matches = []
        for pattern in credit_card_patterns:
            for page_num, page in enumerate(text_pages):
                page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
                for match in page_matches:
                    cc_matches.append({
                        "value": match,
                        "page": page_num + 1
                    })
        
        if cc_matches:
            findings["Credit Card Numbers"] = cc_matches
            print(f" |  Found {len(cc_matches)} credit card number(s)")
            
        # CVV/CVC Codes
        cvv_patterns = [
            r"\bCVV\s*:?\s*\d{3,4}\b",  # CVV: 123
            r"\bCVC\s*:?\s*\d{3,4}\b",  # CVC: 123
            r"\bCV2\s*:?\s*\d{3,4}\b",  # CV2: 123
            r"\bSecurity Code\s*:?\s*\d{3,4}\b",  # Security Code: 123
            r"\b\d{3,4}\s+\(CVV\)\b",  # 123 (CVV)
            r"\b\d{3,4}\s+\(CVC\)\b",  # 123 (CVC)
            r"\b\d{3,4}\s+\(Security Code\)\b",  # 123 (Security Code)
            r"\bCSC\s*:?\s*\d{3,4}\b",  # CSC: 123 (Card Security Code)
            r"\bCID\s*:?\s*\d{3,4}\b",  # CID: 123 (Card Identification Number used by AmEx)
            r"\bCVN\s*:?\s*\d{3,4}\b",  # CVN: 123 (Card Verification Number)
            r"\bCVD\s*:?\s*\d{3,4}\b",  # CVD: 123 (Card Verification Data)
        ]
        
        cvv_matches = []
        for pattern in cvv_patterns:
            for page_num, page in enumerate(text_pages):
                page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
                for match in page_matches:
                    cvv_matches.append({
                        "value": match,
                        "page": page_num + 1
                    })
        
        if cvv_matches:
            findings["CVV/CVC Codes"] = cvv_matches
            print(f" |  Found {len(cvv_matches)} CVV/CVC code(s)")
            
        # Card Expiration Dates
        expiry_patterns = [
            r"\bExpiry\s*:?\s*\d{1,2}/\d{2,4}\b",  # Expiry: 05/26
            r"\bExpiration\s*:?\s*\d{1,2}/\d{2,4}\b",  # Expiration: 05/26
            r"\bExp\s*:?\s*\d{1,2}/\d{2,4}\b",  # Exp: 05/26
            r"\bValid Thru\s*:?\s*\d{1,2}/\d{2,4}\b",  # Valid Thru: 05/26
            r"\bExp\. Date\s*:?\s*\d{1,2}/\d{2,4}\b"  # Exp. Date: 05/26
        ]
        
        expiry_matches = []
        for pattern in expiry_patterns:
            for page_num, page in enumerate(text_pages):
                page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
                for match in page_matches:
                    expiry_matches.append({
                        "value": match,
                        "page": page_num + 1
                    })
        
        if expiry_matches:
            findings["Card Expiration Dates"] = expiry_matches
            print(f" |  Found {len(expiry_matches)} card expiration date(s)")

        # BIC/SWIFT Codes
        bic_patterns = [
            r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",  # Standard BIC/SWIFT format
            r"\bBIC\s*:?\s*[A-Z0-9]{8,11}\b",
            r"\bSWIFT\s*:?\s*[A-Z0-9]{8,11}\b"
        ]
        
        bic_matches = []
        for pattern in bic_patterns:
            for page_num, page in enumerate(text_pages):
                page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
                for match in page_matches:
                    bic_matches.append({
                        "value": match,
                        "page": page_num + 1
                    })
        
        if bic_matches:
            findings["BIC/SWIFT Codes"] = bic_matches
            print(f" |  Found {len(bic_matches)} BIC/SWIFT code(s)")

        # Custom mask
        if args.mask:
            pattern = r'\b' + re.escape(args.mask) + r'\b'
            custom_matches = []
            for page_num, page in enumerate(text_pages):
                page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
                for match in page_matches:
                    custom_matches.append({
                        "value": match,
                        "page": page_num + 1
                    })
            
            if custom_matches:
                findings["Custom Mask"] = custom_matches
                print(f" |  Found {len(custom_matches)} custom pattern match(es)")

        # IBAN Numbers
        if args.iban:
            iban_patterns = [
                r'\b[A-Z]{2}[0-9]{2}(?:[ ]?[0-9]{4}){4}(?!(?:[ ]?[0-9]){3})(?:[ ]?[0-9]{1,2})?\b',  # Standard format
                r'\bIBAN\s*:?\s*[A-Z]{2}[0-9]{2}[0-9A-Z]{10,30}\b'  # IBAN with label
            ]
            
            iban_matches = []
            for pattern in iban_patterns:
                for page_num, page in enumerate(text_pages):
                    page_matches = re.findall(pattern, page, flags=re.IGNORECASE)
                    for match in page_matches:
                        iban_matches.append({
                            "value": match,
                            "page": page_num + 1
                        })
            
            if iban_matches:
                findings["IBAN Numbers"] = iban_matches
                print(f" |  Found {len(iban_matches)} IBAN number(s)")

        # Image scan (if requested)
        if args.redact_images and tesseract_installed:
            print("\n[i] Scanning images for sensitive information...")
            image_findings = []
            
            # Define pattern groups for image scanning
            pattern_groups = {
                "Credit Cards": [
                    r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                    r"\b\d{13,16}\b"
                ],
                "CVV/CVC": [
                    r"\bCVV\s*:?\s*\d{3,4}\b",
                    r"\bCVC\s*:?\s*\d{3,4}\b"
                ],
                "Phone Numbers": [
                    r"\b(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}\b"
                ],
                "Email Addresses": [
                    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                ]
            }
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                images = page.get_images(full=True)
                
                if not images:
                    continue
                    
                print(f" |  Scanning {len(images)} images on Page {page_num+1}")
                
                for img_index, img_info in enumerate(images):
                    try:
                        xref = img_info[0]
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        
                        # Try multiple OCR approaches for better accuracy
                        text = pytesseract.image_to_string(pil_image)
                        
                        # If image is large, also try with higher DPI setting
                        if pil_image.width > 1000 or pil_image.height > 1000:
                            text_hq = pytesseract.image_to_string(
                                pil_image, 
                                config='--oem 1 --psm 3 -c preserve_interword_spaces=1'
                            )
                            text += "\n" + text_hq
                        
                        if text.strip():
                            image_finding = {
                                "page": page_num + 1,
                                "image_index": img_index + 1,
                                "dimensions": f"{pil_image.width}x{pil_image.height}",
                                "findings": {}
                            }
                            
                            found_something = False
                            
                            # Check for each pattern group
                            for data_type, patterns in pattern_groups.items():
                                matches = []
                                for pattern in patterns:
                                    pattern_matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                                    if pattern_matches:
                                        matches.extend(pattern_matches)
                                        found_something = True
                                
                                if matches:
                                    unique_matches = list(set(matches))
                                    image_finding["findings"][data_type] = unique_matches
                                    print(f" |  Found {len(unique_matches)} {data_type} in image {img_index+1} on Page {page_num+1}")
                            
                            if found_something:
                                image_findings.append(image_finding)
                    except Exception as e:
                        print(f" |  Error scanning image {img_index+1} on Page {page_num+1}: {e}")
            
            if image_findings:
                findings["Images"] = image_findings
                print(f" |  Found sensitive information in {len(image_findings)} image(s)")
        
        # Generate comprehensive report
        total_count = 0
        by_category = {}
        
        for category, items in findings.items():
            if isinstance(items, list):
                item_count = len(items)
                total_count += item_count
                by_category[category] = item_count
        
        report = {
            "file": str(filepath),
            "scan_timestamp": datetime.now().isoformat(),
            "findings_summary": {
                "total_findings": total_count,
                "by_category": by_category
            },
            "findings": findings
        }
        
        # Special handling for image findings count
        if "Images" in findings:
            image_count = len(findings["Images"])
            report["findings_summary"]["by_category"]["Images"] = image_count
            # Adjust total count
            image_items_count = sum(len(img_finding["findings"].get(cat, [])) 
                                for img_finding in findings["Images"] 
                                for cat in img_finding["findings"])
            report["findings_summary"]["total_findings"] += image_items_count
        
        # Save report to JSON file
        report_path = filepath.parent / f"{filepath.stem}_sensitivity_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n[i] Sensitivity report saved to: {report_path}")
        
        # Print summary
        print("\n[SENSITIVITY FINDINGS SUMMARY]")
        print(f"Total items found: {report['findings_summary']['total_findings']}")
        print("By category:")
        for category, count in report['findings_summary']['by_category'].items():
            print(f"  - {category}: {count} item(s)")
        
        # Suggest redaction if needed
        if report['findings_summary']['total_findings'] > 0:
            print("\n[RECOMMENDATION]")
            print("Sensitive information was found in this document. To redact it, run:")
            cmd = f"python pdf_redactor.py -i \"{filepath}\""
            
            for arg in sys.argv[1:]:
                if arg != "--report-only" and not arg.startswith("-i") and not arg.startswith("--input"):
                    cmd += f" {arg}"
            
            print(f"  {cmd}")

    def redact_document(self):
        """Main method to handle document redaction"""
        # Check if input file exists
        input_path = Path(self.config.input_pdf)
        if not input_path.exists():
            print(f"\n[Error] Input file not found: {input_path}")
            return
            
        # Handle text files differently
        if input_path.suffix.lower() == '.txt':
            self.process_text_file(input_path, self.config)
            return
            
        # Process PDF files
        try:
            self.process_file(input_path, self.config)
        except Exception as e:
            print(f"\n[Error] Failed to process PDF: {e}")
            raise

    def find_phone_matches(self, page, page_num):
        """Find matches for phone numbers"""
        print(f"\n[i] Searching for Phone Numbers...")
        
        # Get the page text
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # Phone number patterns - More precise to avoid false positives
        patterns = [
            # US/Canada format with various separators - must have common phone prefixes
            r"\b(?:Phone|Tel|Mobile|Cell|Contact|Call|Fax)?\s*(?::|#|number|is|at)?\s*(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
            
            # International format with + prefix
            r"\b\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b",
            
            # Common phone number labels with numbers
            r"\b(?:phone|tel|telephone|mobile|cell|fax|work|home|office)[:.\s]+(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
            
            # Extension formats
            r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})(?:[-.\s]?(?:ext|x|extension)[-.\s]?\d{1,5})?\b"
        ]
        
        # Skip patterns that look like credit card numbers
        skip_patterns = [
            r"\b(?:\d{4}[-\s]?){4}\b",  # 16 digits with separators
            r"\b\d{16}\b",               # 16 digits without separators
            r"\b\d{13}\b",               # 13 digits
            r"\b\d{15}\b",               # 15 digits
            r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|3(?:0[0-5]|[68]\d)\d{11}|6(?:011|5\d{2})\d{12})\b"  # Card issuer patterns
        ]
        
        # Find all matches and create redactions
        redactions = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                match_text = match.group(0)
                
                # Skip if it matches a credit card pattern
                is_credit_card = any(re.search(cc_pattern, match_text) for cc_pattern in skip_patterns)
                if is_credit_card:
                    continue
                
                # Skip if it's part of a heading/label and preserve_headings is True
                if self.config.preserve_headings and self.is_heading(match_text, self.config, lang_code):
                    continue
                
                # Skip if it looks like a year (e.g., 2023)
                if re.match(r"\b(?:19|20)\d{2}\b", match_text):
                    continue
                    
                # Skip if it looks like a page number or section number
                if re.match(r"\b[1-9]\d{0,3}\b", match_text):
                    continue
                
                # Find match on page with its coordinates
                instances = page.search_for(match_text)
                for inst in instances:
                    # Create redaction for this match
                    redaction = {
                        "type": "Phone Number",
                        "match": match_text,
                        "rect": inst,
                        "quads": [inst.quad],
                        "page": page_num
                    }
                    
                    # Choose color based on config
                    if self.config.use_blur:
                        redaction["text"] = "*" * len(match_text)
                    else:
                        color = self.COLORS.get(self.config.color, self.COLORS["black"])
                        redaction["fill"] = color
                    
                    redactions.append(redaction)
        
        print(f"[i] Found {len(redactions)} phone number matches on page {page_num + 1}")
        return redactions

    def find_email_matches(self, page, page_num):
        """Find matches for email addresses"""
        print(f"\n[i] Searching for Email Addresses...")
        
        # Get the page text
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # Standard email pattern
        patterns = [
            # Basic email pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            
            # Email with common prefixes/labels
            r'\b(email|e-mail|mail)[:.\s]+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
            
            # Obfuscated emails (with "at" and "dot")
            r'\b[A-Za-z0-9._%+-]+\s+at\s+[A-Za-z0-9.-]+\s+dot\s+[A-Z|a-z]{2,}\b'
        ]
        
        # Language-specific patterns
        lang_patterns = self.get_language_specific_patterns(lang_code).get("email", [])
        if lang_patterns:
            patterns.extend(lang_patterns)
        
        # Find all matches and create redactions
        redactions = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                match_text = match.group(0)
                
                # Extract actual email if it's in a labeled format
                if ":" in match_text and "@" in match_text:
                    parts = match_text.split(":")
                    for part in parts:
                        if "@" in part:
                            match_text = part.strip()
                            break
                
                # Skip if it's part of a heading/label and preserve_headings is True
                if self.config.preserve_headings and self.is_heading(match_text, self.config, lang_code):
                    continue
                
                # Find match on page with its coordinates
                instances = page.search_for(match_text)
                for inst in instances:
                    # Create redaction for this match
                    redaction = {
                        "type": "Email Address",
                        "match": match_text,
                        "rect": inst,  # Rectangle coordinates of the match
                        "quads": [inst.quad],  # Convert rect to quad for more precise redaction
                        "page": page_num
                    }
                    
                    # Choose color based on config
                    if self.config.use_blur:
                        redaction["text"] = "*" * len(match_text)  # Replace with asterisks for blur effect
                    else:
                        color = self.COLORS.get(self.config.color, self.COLORS["black"])
                        redaction["fill"] = color
                    
                    redactions.append(redaction)
        
        print(f"[i] Found {len(redactions)} email address matches on page {page_num + 1}")
        return redactions

    def find_credit_card_matches(self, page, page_num):
        """Find matches for credit card numbers"""
        print(f"\n[i] Searching for Credit Card Numbers...")
        
        # Get the page text
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # Credit card patterns for major card providers
        patterns = [
            # Visa: 13 or 16 digits starting with 4
            r"\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            r"\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{1,4}\b",
            
            # Mastercard: 16 digits starting with 51-55 or 2221-2720
            r"\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            r"\b2[2-7][2-7]\d[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            
            # American Express: 15 digits starting with 34 or 37
            r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b",
            
            # Discover: 16 digits starting with 6011, 622126-622925, 644-649, or 65
            r"\b6011[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            r"\b65\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            r"\b64[4-9]\d[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            
            # Common labels with credit card numbers
            r"\b(?:credit\s+card|card\s+number|cc\s+number|cc\s*#|card\s*#)[:.\s]+(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b",
            r"\b(?:visa|mastercard|amex|discover)[:.\s]+(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b"
        ]
        
        # Skip patterns that look like phone numbers
        skip_patterns = [
            r"\b\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # Standard phone format
            r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",  # (123) 456-7890
            r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"   # 123-456-7890
        ]
        
        # Find all matches and create redactions
        redactions = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                match_text = match.group(0)
                
                # Skip if it matches a phone number pattern
                is_phone = any(re.search(phone_pattern, match_text) for phone_pattern in skip_patterns)
                if is_phone:
                    continue
                
                # Skip if it's part of a heading/label and preserve_headings is True
                if self.config.preserve_headings and self.is_heading(match_text, self.config, lang_code):
                    continue
                
                # Find match on page with its coordinates
                instances = page.search_for(match_text)
                for inst in instances:
                    # Create redaction for this match
                    redaction = {
                        "type": "Credit Card Number",
                        "match": match_text,
                        "rect": inst,
                        "quads": [inst.quad],
                        "page": page_num
                    }
                    
                    # Choose color based on config
                    if self.config.use_blur:
                        redaction["text"] = "*" * len(match_text)
                    else:
                        color = self.COLORS.get(self.config.color, self.COLORS["black"])
                        redaction["fill"] = color
                    
                    redactions.append(redaction)
        
        print(f"[i] Found {len(redactions)} credit card matches on page {page_num + 1}")
        return redactions

    def find_cvv_matches(self, page, page_num):
        """Find matches for CVV/CVC security codes"""
        print(f"\n[i] Searching for CVV/CVC Codes...")
        
        # Get the page text
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # CVV/CVC patterns - More precise to avoid false positives
        patterns = [
            # Common CVV/CVC patterns with labels
            r"\b(?:cvv|cvc|cvv2|cvc2|security\s+code|card\s+security\s+code|verification\s+code|security\s+number)[:.\s]+(\d{3,4})\b",
            
            # CVV/CVC with parentheses
            r"\b(\d{3,4})\s*\((?:cvv|cvc|security\s+code)\)",
            
            # CVV/CVC near credit card numbers (within reasonable distance)
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\s+(?:cvv|cvc|security\s+code)?[:.\s]*(\d{3,4})\b",
            
            # Labeled CVV/CVC in various formats
            r"\b(?:cvv|cvc|security)\s*(?:number|code|verification)?\s*[:.\s]+(\d{3,4})\b"
        ]
        
        # Language-specific patterns
        lang_patterns = self.get_language_specific_patterns(lang_code).get("cvv", [])
        if lang_patterns:
            patterns.extend(lang_patterns)
        
        # Find all matches and create redactions
        redactions = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Check if we have a pattern with capture groups
                if "(" in pattern and len(match.groups()) > 0:
                    # Use the first capture group for the CVV digits
                    match_text = match.group(1)
                else:
                    match_text = match.group(0)
                
                # Skip if it's part of a heading/label and preserve_headings is True
                if self.config.preserve_headings and self.is_heading(match_text, self.config, lang_code):
                    continue
                
                # Skip if it looks like a year (e.g., 2023)
                if re.match(r"\b(?:19|20)\d{2}\b", match_text):
                    continue
                    
                # Skip if it looks like a page number or section number
                if re.match(r"\b[1-9]\d{0,2}\b", match_text):
                    continue
                
                # Find match on page with its coordinates
                instances = page.search_for(match_text)
                for inst in instances:
                    # Create redaction for this match
                    redaction = {
                        "type": "CVV/CVC Code",
                        "match": match_text,
                        "rect": inst,
                        "quads": [inst.quad],
                        "page": page_num
                    }
                    
                    # Choose color based on config
                    if self.config.use_blur:
                        redaction["text"] = "*" * len(match_text)
                    else:
                        color = self.COLORS.get(self.config.color, self.COLORS["black"])
                        redaction["fill"] = color
                    
                    redactions.append(redaction)
        
        print(f"[i] Found {len(redactions)} CVV/CVC matches on page {page_num + 1}")
        return redactions

    def find_cc_expiration_matches(self, page, page_num):
        """Find matches for credit card expiration dates"""
        print(f"\n[i] Searching for Card Expiration Dates...")
        
        # Get the page text
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # Expiration date patterns
        patterns = [
            # MM/YY format
            r"\b(0[1-9]|1[0-2])[\/\-\s](\d{2})\b",
            
            # MM/YYYY format
            r"\b(0[1-9]|1[0-2])[\/\-\s](20\d{2})\b",
            
            # Common labels with expiration dates
            r"\b(exp|expires|expiration|expiry|valid\s+through|valid\s+until|good\s+through|date)[:.\s]+(0[1-9]|1[0-2])[\/\-\s](\d{2}|20\d{2})\b",
            
            # Text formats
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b"
        ]
        
        # Language-specific patterns
        lang_patterns = self.get_language_specific_patterns(lang_code).get("cc_expiration", [])
        if lang_patterns:
            patterns.extend(lang_patterns)
        
        # Find all matches and create redactions
        redactions = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                match_text = match.group(0)
                
                # Extract the actual expiration date if it's in a labeled format
                if ":" in match_text:
                    parts = match_text.split(":")
                    for part in parts[1:]:  # Look after the colon
                        if re.search(r"(0[1-9]|1[0-2])[\/\-\s](\d{2}|20\d{2})", part):
                            match_text = part.strip()
                            break
                
                # Skip if it's part of a heading/label and preserve_headings is True
                if self.config.preserve_headings and self.is_heading(match_text, self.config, lang_code):
                    continue
                
                # Find match on page with its coordinates
                instances = page.search_for(match_text)
                for inst in instances:
                    # Create redaction for this match
                    redaction = {
                        "type": "Card Expiration Date",
                        "match": match_text,
                        "rect": inst,
                        "quads": [inst.quad],
                        "page": page_num
                    }
                    
                    # Choose color based on config
                    if self.config.use_blur:
                        redaction["text"] = "*" * len(match_text)
                    else:
                        color = self.COLORS.get(self.config.color, self.COLORS["black"])
                        redaction["fill"] = color
                    
                    redactions.append(redaction)
        
        print(f"[i] Found {len(redactions)} card expiration date matches on page {page_num + 1}")
        return redactions

    def find_aadhaar_matches(self, page, page_num):
        """Find matches for Aadhaar numbers"""
        print(f"\n[i] Searching for Aadhaar Numbers...")
        
        # Get the page text and find all matches
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # Default to English patterns if language is not supported
        if lang_code not in ["hi", "en"]:
            lang_code = "en"
        
        # Aadhaar patterns
        patterns = self.get_language_specific_patterns(lang_code).get("aadhaar", [])
        if lang_code != "hi":  # If not Hindi, use default Aadhaar pattern
            patterns = [
                r"\b\d{4}\s?\d{4}\s?\d{4}\b",  # Standard 12-digit Aadhaar
                r"\bAadhaar(?:\s+Number)?[:.\s]+\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"  # Prefixed with "Aadhaar" in Hindi
            ]
        
        redactions = []
        aadhaar_matches = []
        
        # Process each pattern
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                match_text = match.group(0)
                if self.should_preserve_heading(match_text) and self.config.preserve_headings:
                    print(f" |  Preserving heading/label: {match_text}")
                    continue
                
                # Try to get the rectangle for this match
                match_quads = page.search_for(match_text)
                if match_quads:
                    for quad in match_quads:
                        # Convert quad to rectangle
                        rect = quad.rect
                        # Add redaction
                        if self.config.use_blur:
                            redactions.append((rect, self.blur_text(match_text)))
                        else:
                            redactions.append((rect, self.color_map.get(self.config.color, (0, 0, 0))))
                
                    aadhaar_matches.append(match_text)
        
        # Output the matches
        print(f" |  Found {len(aadhaar_matches)} Aadhaar Numbers on Page {page_num + 1}: {', '.join(aadhaar_matches)}")
        
        # Store redaction information for reporting
        page_key = f"Page {page_num + 1}"
        if page_key not in self.report_data["redacted_items"]:
            self.report_data["redacted_items"][page_key] = {}
        
        self.report_data["redacted_items"][page_key]["Aadhaar Numbers"] = aadhaar_matches
        
        return redactions

    def find_pan_matches(self, page, page_num):
        """Find matches for PAN card numbers"""
        print(f"\n[i] Searching for PAN Numbers...")
        
        # Get the page text and find all matches
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # Default to English patterns if language is not supported
        if lang_code not in ["hi", "en"]:
            lang_code = "en"
        
        # PAN patterns
        patterns = self.get_language_specific_patterns(lang_code).get("pan", [])
        if lang_code != "hi":  # If not Hindi, use default PAN pattern
            patterns = [
                r"\b[A-Z]{5}\d{4}[A-Z]\b",  # Standard PAN format
                r"\bPAN\s*[:.\s]+[A-Z]{5}\d{4}[A-Z]\b"  # With PAN prefix
            ]
        
        redactions = []
        pan_matches = []
        
        # Process each pattern
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                match_text = match.group(0)
                if self.should_preserve_heading(match_text) and self.config.preserve_headings:
                    print(f" |  Preserving heading/label: {match_text}")
                    continue
                
                # Try to get the rectangle for this match
                match_quads = page.search_for(match_text)
                if match_quads:
                    for quad in match_quads:
                        # Convert quad to rectangle
                        rect = quad.rect
                        # Add redaction
                        if self.config.use_blur:
                            redactions.append((rect, self.blur_text(match_text)))
                        else:
                            redactions.append((rect, self.color_map.get(self.config.color, (0, 0, 0))))
                
                    pan_matches.append(match_text)
        
        # Output the matches
        print(f" |  Found {len(pan_matches)} PAN Numbers on Page {page_num + 1}: {', '.join(pan_matches)}")
        
        # Store redaction information for reporting
        page_key = f"Page {page_num + 1}"
        if page_key not in self.report_data["redacted_items"]:
            self.report_data["redacted_items"][page_key] = {}
        
        self.report_data["redacted_items"][page_key]["PAN Numbers"] = pan_matches
        
        return redactions

    def find_iban_matches(self, page, page_num):
        """Find matches for IBAN (International Bank Account Number)"""
        print(f"\n[i] Searching for IBAN Numbers...")
        
        # Get the page text
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # IBAN patterns (general format and country-specific)
        patterns = [
            # General IBAN pattern with country code
            r"\b[A-Z]{2}\d{2}[-\s]?[A-Z0-9]{4}[-\s]?[A-Z0-9]{4}[-\s]?[A-Z0-9]{4}[-\s]?[A-Z0-9]{1,12}\b",
            
            # With IBAN prefix
            r"\b(iban|account)[:.\s]+([A-Z]{2}\d{2}[-\s]?[A-Z0-9]{4}[-\s]?[A-Z0-9]{4}[-\s]?[A-Z0-9]{4}[-\s]?[A-Z0-9]{1,12})\b",
            
            # UK format (GB + 2 digits + 4 letters + 6 digits + 8 digits)
            r"\bGB\d{2}[-\s]?[A-Z]{4}[-\s]?\d{6}[-\s]?\d{8}\b",
            
            # German format (DE + 2 digits + 18 chars)
            r"\bDE\d{2}[-\s]?\d{8}[-\s]?\d{10}\b",
            
            # French format (FR + 2 digits + 10 chars + 11 digits + 2 chars)
            r"\bFR\d{2}[-\s]?\d{5}[-\s]?\d{5}[-\s]?[A-Z0-9]{11}[-\s]?\d{2}\b"
        ]
        
        # Language-specific patterns
        lang_patterns = self.get_language_specific_patterns(lang_code).get("iban", [])
        if lang_patterns:
            patterns.extend(lang_patterns)
        
        # Find all matches and create redactions
        redactions = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                match_text = match.group(0)
                
                # Extract actual IBAN if it's in a labeled format
                if ":" in match_text and any(country in match_text.upper() for country in ["GB", "DE", "FR", "ES", "IT", "NL"]):
                    parts = match_text.split(":")
                    for part in parts:
                        if re.search(r"[A-Z]{2}\d{2}", part.upper()):
                            match_text = part.strip()
                            break
                
                # Skip if it's part of a heading/label and preserve_headings is True
                if self.config.preserve_headings and self.is_heading(match_text, self.config, lang_code):
                    continue
                
                # Find match on page with its coordinates
                instances = page.search_for(match_text)
                for inst in instances:
                    # Create redaction for this match
                    redaction = {
                        "type": "IBAN Number",
                        "match": match_text,
                        "rect": inst,
                        "quads": [inst.quad],
                        "page": page_num
                    }
                    
                    # Choose color based on config
                    if self.config.use_blur:
                        redaction["text"] = "*" * len(match_text)
                    else:
                        color = self.COLORS.get(self.config.color, self.COLORS["black"])
                        redaction["fill"] = color
                    
                    redactions.append(redaction)
        
        print(f"[i] Found {len(redactions)} IBAN matches on page {page_num + 1}")
        return redactions

    def find_bic_matches(self, page, page_num):
        """Find matches for BIC/SWIFT codes"""
        print(f"\n[i] Searching for BIC/SWIFT Codes...")
        
        # Get the page text
        text = page.get_text()
        
        # Get language-specific patterns
        lang_code = self.config.language
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        
        # BIC/SWIFT code patterns
        patterns = [
            # Standard BIC/SWIFT format (8 or 11 characters)
            r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",
            
            # With BIC/SWIFT prefix
            r"\b(bic|swift|code)[:.\s]+([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
        ]
        
        # Language-specific patterns
        lang_patterns = self.get_language_specific_patterns(lang_code).get("bic", [])
        if lang_patterns:
            patterns.extend(lang_patterns)
        
        # Find all matches and create redactions
        redactions = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                match_text = match.group(0)
                
                # Extract actual BIC if it's in a labeled format
                if ":" in match_text:
                    parts = match_text.split(":")
                    for part in parts:
                        if re.search(r"[A-Z]{4}[A-Z]{2}", part.upper()):
                            match_text = part.strip()
                            break
                
                # Skip if it's part of a heading/label and preserve_headings is True
                if self.config.preserve_headings and self.is_heading(match_text, self.config, lang_code):
                    continue
                
                # Find match on page with its coordinates
                instances = page.search_for(match_text)
                for inst in instances:
                    # Create redaction for this match
                    redaction = {
                        "type": "BIC/SWIFT Code",
                        "match": match_text,
                        "rect": inst,
                        "quads": [inst.quad],
                        "page": page_num
                    }
                    
                    # Choose color based on config
                    if self.config.use_blur:
                        redaction["text"] = "*" * len(match_text)
                    else:
                        color = self.COLORS.get(self.config.color, self.COLORS["black"])
                        redaction["fill"] = color
                    
                    redactions.append(redaction)
        
        print(f"[i] Found {len(redactions)} BIC/SWIFT matches on page {page_num + 1}")
        return redactions

    def find_custom_matches(self, page, page_num):
        """Find matches for custom pattern specified by the user"""
        # Check if custom mask is provided
        if not self.config.custom_mask:
            return []
            
        print(f"\n[i] Searching for Custom Pattern Matches...")
        
        # Get the page text
        text = page.get_text()
        
        # Try to compile the custom pattern
        try:
            custom_pattern = re.compile(self.config.custom_mask, re.IGNORECASE)
        except re.error:
            print(f"[!] Error: Invalid custom pattern '{self.config.custom_mask}'")
            return []
        
        # Find all matches and create redactions
        redactions = []
        for match in re.finditer(custom_pattern, text):
            match_text = match.group(0)
            
            # Skip if it's part of a heading/label and preserve_headings is True
            lang_code = self.config.language
            if lang_code == "auto":
                lang_code = self.detect_language(text)
                
            if self.config.preserve_headings and self.is_heading(match_text, self.config, lang_code):
                continue
            
            # Find match on page with its coordinates
            instances = page.search_for(match_text)
            for inst in instances:
                # Create redaction for this match
                redaction = {
                    "type": "Custom Pattern",
                    "match": match_text,
                    "rect": inst,
                    "quads": [inst.quad],
                    "page": page_num
                }
                
                # Choose color based on config
                if self.config.use_blur:
                    redaction["text"] = "*" * len(match_text)
                else:
                    color = self.COLORS.get(self.config.color, self.COLORS["black"])
                    redaction["fill"] = color
                
                redactions.append(redaction)
        
        print(f"[i] Found {len(redactions)} custom pattern matches on page {page_num + 1}")
        return redactions

    def process_text_file(self, filepath: Path, config: RedactionConfig) -> None:
        """Process a text file for redaction"""
        print(f"\n[i] Processing text file: {filepath}")
        
        # Try different encodings
        encodings = ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'ascii', 'iso-8859-1', 'cp1252']
        text = None
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    text = f.read()
                print(f"[i] Successfully read file using {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
                
        if text is None:
            print("[Error] Failed to read file with any known encoding")
            return
            
        # Create a list with just the text content
        text_pages = [text]
        redacted_text = text
        
        # Track redacted items for reporting
        redacted_items = {}
        
        # Credit card numbers (check these first to prevent phone number pattern matches)
        if config.redact_cc:
            credit_card_patterns = [
                r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                r"\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b",
                r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",
                r"\b\d{16}\b",
                r"\b\d{13}\b",
                r"\b\d{15}\b"
            ]
            
            cc_matches = []
            for pattern in credit_card_patterns:
                matches = re.finditer(pattern, redacted_text)
                for match in matches:
                    cc_matches.append(match.group())
                    redacted_text = redacted_text.replace(match.group(), '[REDACTED-CC]')
            
            if cc_matches:
                redacted_items["Credit Card Numbers"] = cc_matches
                
        # Phone numbers
        if config.redact_phone:
            phone_patterns = [
                r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
                r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
                r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",
                r"\b\+\d{1,3}\s?\d{2,3}\s?\d{3,4}\s?\d{3,4}\b"
            ]
            
            phone_matches = []
            for pattern in phone_patterns:
                matches = re.finditer(pattern, redacted_text)
                for match in matches:
                    phone_matches.append(match.group())
                    redacted_text = redacted_text.replace(match.group(), '[REDACTED-PHONE]')
            
            if phone_matches:
                redacted_items["Phone Numbers"] = phone_matches
                
        # Email addresses
        if config.redact_email:
            email_patterns = [
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                r"[a-zA-Z0-9._%+-]+\s+at\s+[a-zA-Z0-9.-]+\s+dot\s+[a-zA-Z]{2,}",
                r"[a-zA-Z0-9._%+-]+\[at\][a-zA-Z0-9.-]+\[dot\][a-zA-Z]{2,}"
            ]
            
            email_matches = []
            for pattern in email_patterns:
                matches = re.finditer(pattern, redacted_text)
                for match in matches:
                    email_matches.append(match.group())
                    redacted_text = redacted_text.replace(match.group(), '[REDACTED-EMAIL]')
            
            if email_matches:
                redacted_items["Email Addresses"] = email_matches
                
        # SSN and other sensitive patterns from mask
        if config.custom_mask:
            mask_pattern = r'\b' + re.escape(config.custom_mask) + r'\b'
            matches = re.finditer(mask_pattern, redacted_text)
            mask_matches = []
            for match in matches:
                mask_matches.append(match.group())
                redacted_text = redacted_text.replace(match.group(), '[REDACTED-MASKED]')
            
            if mask_matches:
                redacted_items["Custom Mask"] = mask_matches
            
        # Save the redacted text
        out_path = Path(config.output_pdf)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(redacted_text)
            
        # Generate redaction report
        self.generate_redaction_report(filepath, out_path, redacted_items)
        
        # Verify redaction if requested
        if config.verify:
            print("\n[i] Verifying redaction...")
            with open(out_path, 'r', encoding='utf-8') as f:
                redacted_content = f.read()
            
            # Check for any remaining sensitive information
            found_sensitive = False
            remaining_sensitive = {}
            
            # Check credit card numbers first
            if config.redact_cc:
                for pattern in credit_card_patterns:
                    matches = re.finditer(pattern, redacted_content)
                    cc_matches = [m.group() for m in matches]
                    if cc_matches:
                        found_sensitive = True
                        remaining_sensitive["Credit Card Numbers"] = cc_matches
            
            # Check phone numbers
            if config.redact_phone:
                for pattern in phone_patterns:
                    matches = re.finditer(pattern, redacted_content)
                    phone_matches = [m.group() for m in matches]
                    if phone_matches:
                        found_sensitive = True
                        remaining_sensitive["Phone Numbers"] = phone_matches
                        
            # Check email addresses
            if config.redact_email:
                for pattern in email_patterns:
                    matches = re.finditer(pattern, redacted_content)
                    email_matches = [m.group() for m in matches]
                    if email_matches:
                        found_sensitive = True
                        remaining_sensitive["Email Addresses"] = email_matches
                    
            # Check custom mask patterns
            if config.custom_mask:
                matches = re.finditer(mask_pattern, redacted_content)
                mask_matches = [m.group() for m in matches]
                if mask_matches:
                    found_sensitive = True
                    remaining_sensitive["Custom Mask"] = mask_matches
                    
            if found_sensitive:
                print("\n[FAILURE] Redaction verification failed - sensitive information still present:")
                print("=" * 80)
                for category, matches in remaining_sensitive.items():
                    print(f"\n{category}:")
                    for match in matches:
                        print(f"  - {match}")
                print("=" * 80)
            else:
                print("\n[SUCCESS] All sensitive information has been properly redacted.")

def print_color_banner():
    """Print a colored banner for the tool"""
    print("\n┌─┐┌─┐┬  ┬┌─┐┌─┐┌─┐")
    print("├┤ │  │  │├─┘└─┐├┤ ")
    print("└─┘└─┘┴─┘┴┴  └─┘└─┘")
    print("        made by moduluz")
    
    print("\nPDF Redactor - Securely redact sensitive information from PDFs")
    print("------------------------------------------------------------------")
    print("Options:")
    print("  --blur              : Use blur-style redaction (asterisks instead of blocks)")
    print("  --color [color]     : Choose redaction color (black, white, red, green, blue)")
    print("  --no-preserve-headings : Redact all matching text, including headings/labels")
    print("  --verify            : Verify redaction after processing")
    print("  --redact-images     : Redact sensitive information in images using OCR")
    print("  --report-only       : Generate a detailed report without performing redactions")
    print("------------------------------------------------------------------")

def print_sensitivity_report_summary(redaction_stats):
    """Print a summary of the sensitivity report"""
    total_items = sum(redaction_stats.values())
    
    print("\n[SENSITIVITY FINDINGS SUMMARY]")
    print(f"Total items found: {total_items}")
    
    if total_items > 0:
        print("By category:")
        for category, count in redaction_stats.items():
            if count > 0:
                print(f"  - {category}: {count} item(s)")

def main():
    parser = argparse.ArgumentParser(description="PDF Redactor Tool")
    parser.add_argument("-i", "--input", required=True, help="Input PDF file path")
    parser.add_argument("-o", "--output", help="Output PDF file path")
    parser.add_argument("--phonenumber", action="store_true", help="Redact phone numbers")
    parser.add_argument("--email", action="store_true", help="Redact email addresses")
    parser.add_argument("--iban", action="store_true", help="Redact IBAN numbers")
    parser.add_argument("--aadhaar", action="store_true", help="Redact Aadhaar numbers (Indian national ID)")
    parser.add_argument("--pan", action="store_true", help="Redact PAN numbers (Indian tax ID)")
    parser.add_argument("--mask", help="Custom text to mask/redact")
    parser.add_argument("--redact-images", action="store_true", help="Redact sensitive information in images using OCR")
    parser.add_argument("--verify", action="store_true", help="Verify redaction after processing")
    parser.add_argument("--no-preserve-headings", action="store_true", help="Don't preserve text that looks like headings/labels")
    parser.add_argument("--blur", action="store_true", help="Use blur-style redaction (asterisks) instead of block redaction")
    parser.add_argument("--color", choices=["black", "white", "red", "green", "blue"], default="black", help="Color for redactions (default: black)")
    parser.add_argument("--report-only", action="store_true", help="Generate a report of sensitive information without performing redactions")
    parser.add_argument("--language", default="auto", help="Set the language for pattern recognition (e.g., 'fr', 'de', 'es', 'hi', 'auto')")
    
    args = parser.parse_args()
    
    # Debug command line args
    print("\n[DEBUG] Command line args:")
    for arg in vars(args):
        print(f"{arg}: {getattr(args, arg)}")
    
    # Determine output path if not specified
    if not args.output:
        input_path = Path(args.input)
        output_path = input_path.parent / f"{input_path.stem}_redacted{input_path.suffix}"
        args.output = str(output_path)
    
    # Create config object
    config = RedactionConfig(
        redact_phone=args.phonenumber,
        redact_email=args.email,
        redact_iban=args.iban,
        redact_cc=args.iban,  # Credit card redaction is tied to IBAN for now
        redact_cvv=args.iban,  # CVV redaction is tied to IBAN for now
        redact_cc_expiration=args.iban,  # CC expiration redaction is tied to IBAN for now
        redact_bic=args.iban,  # BIC redaction is tied to IBAN for now
        redact_bic_label=args.iban,  # BIC label redaction is tied to IBAN for now
        redact_aadhaar=args.aadhaar,  # New Aadhaar redaction option
        redact_pan=args.pan,  # New PAN redaction option
        redact_images=args.redact_images,
        preserve_headings=not args.no_preserve_headings,
        custom_mask=args.mask,
        use_blur=args.blur,
        color=args.color,
        language=args.language,
        input_pdf=args.input,
        output_pdf=args.output,
        report_only=args.report_only,
        verify=args.verify
    )
    
    # Debug the created config object
    print("\n[DEBUG] RedactionConfig object:")
    for field in config.__annotations__:
        print(f"{field}: {getattr(config, field)}")
    
    # Create color banner
    print_color_banner()
    
    # Check if in report-only mode
    if args.report_only:
        print(f"\n[i] Scanning file for sensitive information without redacting: {args.input}")
        redactor = PDFRedactor(config)
        
        # Call the redact_document method to get the number of redactions
        total_redactions = redactor.redact_document()
        
        report_path = f"{os.path.splitext(args.input)[0]}_sensitivity_report.json"
        print(f"\n[i] Sensitivity report saved to: {report_path}")
        
        # Print a summary of the redaction report
        print_sensitivity_report_summary(redactor.redaction_stats)
        
        # Print recommendation
        print("\n[RECOMMENDATION]")
        print(f"Sensitive information was found in this document. To redact it, run:")
        cmd = f"  python pdf_redactor.py -i \"{args.input}\" {args.input}"
        if args.phonenumber:
            cmd += " --phonenumber"
        if args.email:
            cmd += " --email"
        if args.iban:
            cmd += " --iban"
        if args.aadhaar:
            cmd += " --aadhaar"
        if args.pan:
            cmd += " --pan"
        if args.verify:
            cmd += " --verify"
        
        print(cmd)
    else:
        # Run the redaction
        redactor = PDFRedactor(config)
        redactor.redact_document()

if __name__ == "__main__":
    main()
