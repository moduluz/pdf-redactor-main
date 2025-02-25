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
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import spacy
from fuzzywuzzy import process
import io
import pytesseract
from langdetect import detect, DetectorFactory, detect_langs

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
        r"^(Section|Chapter|Title|Part)\s+\d+",  # Section/Chapter indicators
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

    def save_redactions(self, pdf_document: fitz.Document, filepath: Path) -> None:
        """Save redacted PDF to file"""
        print(f"\n[i] Saving changes to '{filepath}'")
        pdf_document.save(filepath)

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
            # Credit card related
            r"CVV\s*:?\s*\d{3,4}",
            r"CVC\s*:?\s*\d{3,4}",
            r"CV2\s*:?\s*\d{3,4}",
            r"Security Code\s*:?\s*\d{3,4}",
            r"\d{3,4}\s+\(CVV\)",
            r"\d{3,4}\s+\(CVC\)",
            r"\d{3,4}\s+\(Security Code\)",
            r"(?:\d{4}[- ]?){3}\d{4}",  # Credit card numbers
            r"\b\d{16}\b",  # Raw 16-digit numbers
            r"\b\d{13}\b",  # Some cards have 13 digits
            r"\b\d{15}\b",  # American Express format (15 digits)
            
            # Other financial identifiers
            r"IBAN\s*:?\s*[A-Z]{2}[0-9]{2}[0-9A-Z]{10,30}",
            r"BIC\s*:?\s*[A-Z0-9]{8,11}",
            r"Account\s*:?\s*\d+",
            r"Account Number\s*:?\s*\d+",
            r"Routing\s*:?\s*\d+",
            r"Routing Number\s*:?\s*\d+",
            
            # Expiration related
            r"Expiry\s*:?\s*\d{1,2}/\d{2,4}",
            r"Expiration\s*:?\s*\d{1,2}/\d{2,4}",
            r"Exp\s*:?\s*\d{1,2}/\d{2,4}",
            r"Valid Thru\s*:?\s*\d{1,2}/\d{2,4}",
            r"Exp\. Date\s*:?\s*\d{1,2}/\d{2,4}",
            
            # Personal identifiers
            r"SSN\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}",
            r"Social Security\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}",
            r"Tax ID\s*:?\s*\d{2}[-]?\d{7}",
            r"Passport\s*:?\s*[A-Z0-9]{6,9}",
            r"Driver'?s? License\s*:?\s*[A-Z0-9]{6,12}",
            
            # Phone numbers
            r"Phone\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"Mobile\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"Cell\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"Telephone\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"Tel\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
            
            # Email addresses
            r"Email\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            r"E-mail\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
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
        
        print("\n[i] Searching for text in images...")
        image_redaction_info = []
        
        # Define all sensitive data patterns
        pattern_groups = {
            "Credit Cards": [
                r"\b(?:\d{4}[- ]?){3}\d{4}\b",
                r"\b\d{13,16}\b",
                r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|3(?:0[0-5]|[68]\d)\d{11}|6(?:011|5\d{2})\d{12})\b"
            ],
            "CVV/CVC": [
                r"\bCVV\s*:?\s*\d{3,4}\b",
                r"\bCVC\s*:?\s*\d{3,4}\b",
                r"\bCV2\s*:?\s*\d{3,4}\b",
                r"\bCSC\s*:?\s*\d{3,4}\b",
                r"\bCID\s*:?\s*\d{3,4}\b"
            ],
            "Expiration Dates": [
                r"\bExp(?:iry|iration)?\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bValid Thru\s*:?\s*\d{1,2}/\d{2,4}\b"
            ],
            "SSN": [
                r"\bSSN\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}\b",
                r"\bSocial Security\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}\b"
            ],
            "Phone Numbers": [
                r"\b(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}\b",
                r"\bPhone\s*:?\s*(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}\b"
            ],
            "Email Addresses": [
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            ],
            "IBAN/BIC": [
                r"\bIBAN\s*:?\s*[A-Z]{2}[0-9]{2}[0-9A-Z]{10,30}\b",
                r"\bBIC\s*:?\s*[A-Z0-9]{8,11}\b"
            ]
        }
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            images = page.get_images(full=True)
            
            if not images:
                continue
                
            print(f" |  Processing {len(images)} images on Page {page_num+1}")
            
            for img_index, img_info in enumerate(images):
                xref = img_info[0]
                try:
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Try multiple OCR approaches for better accuracy
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    
                    # Try with default OCR
                    text = pytesseract.image_to_string(pil_image)
                    
                    # If image is large, also try with higher DPI setting
                    if pil_image.width > 1000 or pil_image.height > 1000:
                        text_hq = pytesseract.image_to_string(
                            pil_image, 
                            config='--oem 1 --psm 3 -c preserve_interword_spaces=1'
                        )
                        text += "\n" + text_hq
                    
                    # Try with different PSM mode for single column of text
                    text_alt = pytesseract.image_to_string(
                        pil_image,
                        config='--psm 6'
                    )
                    text += "\n" + text_alt
                    
                    if text.strip():
                        found_sensitive_data = False
                        found_data_types = []
                        found_matches = {}
                        
                        # Check for each pattern group
                        for data_type, patterns in pattern_groups.items():
                            data_type_matches = []
                            for pattern in patterns:
                                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                                if matches:
                                    found_sensitive_data = True
                                    found_data_types.append(data_type)
                                    data_type_matches.extend(matches)
                                    print(f" |  Found {data_type} in image {img_index+1} on Page {page_num+1}")
                            
                            if data_type_matches:
                                found_matches[data_type] = list(set(data_type_matches))
                        
                        # If sensitive info found, redact the entire image
                        if found_sensitive_data:
                            print(f" |  Redacting image containing: {', '.join(found_data_types)}")
                            
                            # Get the image rectangle
                            img_rect = None
                            for rect, xref_obj in zip(page.get_image_rects(), page.get_images(full=True)):
                                if xref_obj[0] == xref:
                                    img_rect = rect
                                    break
                            
                            if img_rect:
                                # Apply redaction based on config
                                if config.use_blur:
                                    # Use blur style redaction (semi-transparent with text)
                                    blur_text = "[IMAGE REDACTED]"
                                    fill_color = list(self.COLORS[config.color])
                                    fill_color.append(0.5)  # Add transparency
                                    
                                    annot = page.add_redact_annot(
                                        quad=img_rect,
                                        text=blur_text,
                                        text_color=self.COLORS["black"],
                                        fill=fill_color,
                                        cross_out=False
                                    )
                                else:
                                    # Use standard block redaction
                                    page.add_redact_annot(img_rect, fill=fitz.utils.getColor(config.color))
                                
                                page.apply_redactions()
                                
                                # Record redaction info for reporting
                                image_info = {
                                    "page": page_num + 1,
                                    "image_index": img_index + 1,
                                    "width": pil_image.width,
                                    "height": pil_image.height,
                                    "redaction_type": "blur" if config.use_blur else "block",
                                    "sensitive_data_found": found_matches
                                }
                                image_redaction_info.append(image_info)
                except Exception as e:
                    print(f" |  Error processing image {img_index+1} on Page {page_num+1}: {e}")
                    
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
                r"\bCVV\s*:?\s*\d{3,4}\b",
                r"\bCVC\s*:?\s*\d{3,4}\b",
                r"\bCV2\s*:?\s*\d{3,4}\b",
                r"\bSecurity Code\s*:?\s*\d{3,4}\b",
                r"\bCSC\s*:?\s*\d{3,4}\b",
                r"\bCID\s*:?\s*\d{3,4}\b",
                r"(?<!\d)\d{3,4}(?!\d)"  # Isolated 3-4 digit numbers that might be CVV
            ],
            "Expiration Dates": [
                r"\bExpiry\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bExpiration\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bExp\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bValid Thru\s*:?\s*\d{1,2}/\d{2,4}\b",
                r"\bExp\.\s*Date\s*:?\s*\d{1,2}/\d{2,4}\b"
            ],
            "Phone Numbers": [
                r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
                r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
                r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b"
            ],
            "Email Addresses": [
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            ],
            "IBAN/BIC": [
                r"\bIBAN\s*:?\s*[A-Z]{2}[0-9]{2}[0-9A-Z]{10,30}\b",
                r"\bBIC\s*:?\s*[A-Z0-9]{8,11}\b",
                r"\bSWIFT\s*:?\s*[A-Z0-9]{8,11}\b"
            ],
            "SSN/Government IDs": [
                r"\bSSN\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}\b",
                r"\bSocial Security\s*:?\s*\d{3}[-]?\d{2}[-]?\d{4}\b",
                r"\b\d{3}-\d{2}-\d{4}\b"  # Raw SSN format
            ],
            "Custom Patterns": []
        }
        
        # Add any custom patterns to the appropriate category or to "Custom Patterns"
        for pattern in sensitive_patterns:
            added = False
            for category, patterns in pattern_categories.items():
                if pattern in patterns:
                    added = True
                    break
            if not added:
                pattern_categories["Custom Patterns"].append(pattern)
        
        # Check each page individually for more precise reporting
        page_results = {}
        for page_num, page_text in enumerate(text_pages):
            page_results[page_num + 1] = {}
            
            for category, patterns in pattern_categories.items():
                category_matches = []
                for pattern in patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        for match in matches:
                            # Filter out false positives (e.g., short numbers that aren't CVVs)
                            if pattern == r"(?<!\d)\d{3,4}(?!\d)":
                                # Skip if this looks like a page number, section, or year
                                if re.match(r"\b(19|20)\d{2}\b", match):  # Year
                                    continue
                                if re.match(r"\b[1-9]\d{0,2}\b", match) and len(match) < 4:  # Likely a number < 1000
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

    def process_file(self, filepath: Path, args: argparse.Namespace) -> None:
        """Process a single PDF file"""
        pdf_document = self.load_pdf(filepath)
        text_pages = self.ocr_pdf(pdf_document)
        
        # Collect all patterns for redaction and later verification
        sensitive_patterns = []
        
        # Track redacted items for reporting
        redacted_items = {}

        # Phone numbers - Improved detection with international formats
        if args.phonenumber:
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
            self.redact_matches(pdf_document, phone_matches, self.config)
            
            if phone_matches:
                redacted_items["Phone Numbers"] = phone_matches

        # Email addresses - Enhanced pattern
        if args.email:
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
                
            self.redact_matches(pdf_document, all_email_matches, self.config)
            
            if all_email_matches:
                redacted_items["Email Addresses"] = all_email_matches

        # Credit Card Numbers - Enhanced pattern to catch more formats
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
            self.redact_matches(pdf_document, credit_card_matches, self.config)
            
        if credit_card_matches_all:
            redacted_items["Credit Card Numbers"] = list(set(credit_card_matches_all))

        # CVV/CVC Codes - More comprehensive patterns
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
            self.redact_matches(pdf_document, cvv_matches, self.config)
            
        if cvv_matches_all:
            redacted_items["CVV/CVC Codes"] = list(set(cvv_matches_all))
            
        # Card Expiration Dates
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
            self.redact_matches(pdf_document, expiry_matches, self.config)
            
        if expiry_matches_all:
            redacted_items["Card Expiration Dates"] = list(set(expiry_matches_all))

        # BIC Codes - Improved pattern
        bic_pattern = r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"  # Standard BIC/SWIFT format
        sensitive_patterns.append(bic_pattern)
        bic_matches = self.find_matches(text_pages, bic_pattern, "BIC/SWIFT Codes")
        self.redact_matches(pdf_document, bic_matches, self.config)
        
        # Also look for BIC labels with content
        bic_label_pattern = r"\bBIC\s*:?\s*[A-Z0-9]{8,11}\b"
        sensitive_patterns.append(bic_label_pattern)
        bic_label_matches = self.find_matches(text_pages, bic_label_pattern, "BIC Labels")
        self.redact_matches(pdf_document, bic_label_matches, self.config)
        
        if bic_matches or bic_label_matches:
            redacted_items["BIC/SWIFT Codes"] = list(set(bic_matches + bic_label_matches))

        # Custom mask
        if args.mask:
            pattern = r'\b' + re.escape(args.mask) + r'\b'
            sensitive_patterns.append(pattern)
            matches = self.find_matches(text_pages, pattern, "Custom Mask matches")
            self.redact_matches(pdf_document, matches, self.config)
            if matches:
                redacted_items["Custom Mask"] = matches

        # IBAN - Improved pattern
        if args.iban:
            iban_patterns = [
                r'\b[A-Z]{2}[0-9]{2}(?:[ ]?[0-9]{4}){4}(?!(?:[ ]?[0-9]){3})(?:[ ]?[0-9]{1,2})?\b',  # Standard format
                r'\bIBAN\s*:?\s*[A-Z]{2}[0-9]{2}[0-9A-Z]{10,30}\b'  # IBAN with label
            ]
            sensitive_patterns.extend(iban_patterns)
            iban_matches_all = []
            for pattern in iban_patterns:
                ibans = self.find_matches(text_pages, pattern, "IBANs")
                iban_matches_all.extend(ibans)
                self.redact_matches(pdf_document, ibans, self.config)
                
            if iban_matches_all:
                redacted_items["IBAN Numbers"] = list(set(iban_matches_all))

        # Image redaction tracking
        if args.redact_images:
            image_redaction_info = self.redact_images(pdf_document, self.config)
            if image_redaction_info:
                redacted_items["Images"] = image_redaction_info

        # Save results
        out_path = filepath.parent / f"{filepath.stem}_redacted{filepath.suffix}"
        self.save_redactions(pdf_document, out_path)
        
        # Generate redaction report
        self.generate_redaction_report(filepath, out_path, redacted_items)
        
        # Verify redaction if requested
        if args.verify:
            self.verify_redaction(out_path, sensitive_patterns)
            
    def generate_redaction_report(self, original_path, redacted_path, redacted_items):
        """Generate a detailed report of redactions performed"""
        report = {
            "original_file": str(original_path),
            "redacted_file": str(redacted_path),
            "timestamp": datetime.now().isoformat(),
            "redaction_summary": {
                "total_items_redacted": sum(len(items) for items in redacted_items.values()),
                "by_category": {
                    category: len(items) for category, items in redacted_items.items()
                }
            },
            "redacted_items": redacted_items
        }
        
        report_path = original_path.parent / f"{original_path.stem}_redaction_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"[i] Redaction report saved to: {report_path}")
        
        # Also print a summary to console
        print("\n[REDACTION SUMMARY]")
        print(f"Total items redacted: {report['redaction_summary']['total_items_redacted']}")
        print("By category:")
        for category, count in report['redaction_summary']['by_category'].items():
            print(f"  - {category}: {count} item(s)")

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
        """Redact the document based on the current configuration"""
        doc = fitz.open(self.config.input_pdf)
        total_redactions = 0
        
        # Debug configuration 
        print("\n[DEBUG] Configuration values:")
        print(f"redact_phone: {self.config.redact_phone}")
        print(f"redact_email: {self.config.redact_email}")
        print(f"redact_iban: {self.config.redact_iban}")
        print(f"redact_aadhaar: {self.config.redact_aadhaar}")
        print(f"redact_pan: {self.config.redact_pan}")
        print(f"language: {self.config.language}")
        
        # Detect language or use specified language
        lang_code = self.config.language
        if lang_code == "auto":
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    detected_lang = self.detect_language(text)
                    print(f" |  Detected language for page {page_num + 1}: {detected_lang}")
        
        # Process each page
        for page_num, page in enumerate(doc):
            redactions = []
            
            # Apply various redaction types based on config
            if self.config.redact_phone:
                phone_redactions = self.find_phone_matches(page, page_num)
                redactions.extend(phone_redactions)
                self.redaction_stats["Phone Numbers"] += len(phone_redactions)
            
            if self.config.redact_email:
                email_redactions = self.find_email_matches(page, page_num)
                redactions.extend(email_redactions)
                self.redaction_stats["Email Addresses"] += len(email_redactions)
            
            if self.config.redact_cc:
                cc_redactions = self.find_credit_card_matches(page, page_num)
                redactions.extend(cc_redactions)
                self.redaction_stats["Credit Card Numbers"] += len(cc_redactions)
                
                cvv_redactions = self.find_cvv_matches(page, page_num)
                redactions.extend(cvv_redactions)
                self.redaction_stats["CVV/CVC Codes"] += len(cvv_redactions)
                
                exp_redactions = self.find_cc_expiration_matches(page, page_num)
                redactions.extend(exp_redactions)
                self.redaction_stats["Card Expiration Dates"] += len(exp_redactions)
            
            if self.config.redact_iban:
                iban_redactions = self.find_iban_matches(page, page_num)
                redactions.extend(iban_redactions)
                self.redaction_stats["IBAN Numbers"] += len(iban_redactions)
                
                bic_redactions = self.find_bic_matches(page, page_num)
                redactions.extend(bic_redactions)
                self.redaction_stats["BIC/SWIFT Codes"] += len(bic_redactions)
            
            # New for Indian sensitive data
            if self.config.redact_aadhaar:
                print("\n[DEBUG] Aadhaar detection enabled")
                aadhaar_redactions = self.find_aadhaar_matches(page, page_num)
                redactions.extend(aadhaar_redactions)
                self.redaction_stats["Aadhaar Numbers"] += len(aadhaar_redactions)
            else:
                print("\n[DEBUG] Aadhaar detection disabled")
                
            if self.config.redact_pan:
                print("\n[DEBUG] PAN detection enabled")
                pan_redactions = self.find_pan_matches(page, page_num)
                redactions.extend(pan_redactions)
                self.redaction_stats["PAN Numbers"] += len(pan_redactions)
            
            if self.config.custom_mask:
                custom_redactions = self.find_custom_matches(page, page_num)
                redactions.extend(custom_redactions)
                self.redaction_stats["Custom Pattern"] += len(custom_redactions)
            
            # Apply redactions to this page
            if not self.config.report_only and redactions:
                page.apply_redactions(redactions)
                total_redactions += len(redactions)
        
        # Process images if configured
        if self.config.redact_images and tesseract_installed:
            self.process_images(doc)
        
        # Save the redacted document
        if not self.config.report_only and total_redactions > 0:
            output_path = self.config.output_pdf
            print(f"\n[i] Saving changes to '{output_path}'")
            doc.save(output_path, encryption=False)
        
        # Generate and save report
        self.generate_report(doc)
        
        # Verify redaction if requested
        if self.config.verify and not self.config.report_only:
            self.verify_redaction(doc)
        
        doc.close()
        return total_redactions

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
                r"\bAadhaar(?:\s+Number)?[:.\s]+\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"  # Prefixed with "Aadhaar"
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