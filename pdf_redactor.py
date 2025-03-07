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
import numpy as np
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pdf_redactor.log')
    ]
)
logger = logging.getLogger(__name__)

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
                    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # US/Canada
                    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
                    r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",
                    r"\b(?:\+\d{1,3}[-.\s]?)?\d{1,4}[-.\s]?\d{2,4}[-.\s]?\d{4}\b"  # International
                ],
                "email": [
                    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
                    r"\b[a-zA-Z0-9._%+-]+(?:@|\[at\])[a-zA-Z0-9.-]+(?:\.|\[dot\])[a-zA-Z]{2,}\b"  # Handle obfuscated emails
                ],
                "credit_card": [
                    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",  # Major card types
                    r"\b(?:\d{4}[-\s]?){4}\b",  # Formatted with spaces/dashes
                    r"\b\d{16}\b"  # Raw 16 digits
                ],
                "cvv": [
                    r"\b(?:CVV|CVC|CVV2|CID)[\s:]*\d{3,4}\b",
                    r"\b(?:security code|card code)[\s:]*\d{3,4}\b",
                    r"\b\d{3,4}(?=\s*(?:CVV|CVC|CVV2|CID))\b"
                ],
                "expiration": [
                    r"\b(?:0[1-9]|1[0-2])[-/](?:[0-9]{2}|2[0-9]{3})\b",  # MM/YY or MM/YYYY
                    r"\b(?:0[1-9]|1[0-2])[-/](?:[0-9]{2})\b",  # MM/YY
                    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[,\s]+\d{4}\b"  # Month YYYY
                ],
                "iban": [
                    r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b",
                    r"\b(?:IBAN|International Bank Account Number)[\s:]*[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b"
                ],
                "bic": [
                    r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",
                    r"\b(?:BIC|SWIFT)[\s:]*[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"
                ],
                "aadhaar": [
                    r"\b\d{4}\s?\d{4}\s?\d{4}\b",
                    r"\b(?:Aadhaar|आधार)[\s:]*\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
                ],
                "pan": [
                    r"\b[A-Z]{5}\d{4}[A-Z]\b",
                    r"\b(?:PAN|Permanent Account Number)[\s:]*[A-Z]{5}\d{4}[A-Z]\b"
                ]
            },
            "hi": {
                "phone": [
                    r"\b(?:\+91[-\s]?)?[6789]\d{9}\b",
                    r"\b0\d{2,4}[-\s]?\d{6,8}\b"
                ],
                "aadhaar": [
                    r"\b\d{4}\s?\d{4}\s?\d{4}\b",
                    r"\b(?:आधार|Aadhaar)[\s:]*\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                    r"\bUID[\s:]*\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
                ],
                "pan": [
                    r"\b[A-Z]{5}\d{4}[A-Z]\b",
                    r"\b(?:पैन|PAN)[\s:]*[A-Z]{5}\d{4}[A-Z]\b"
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
        """Enhanced heading detection with language support and common patterns"""
        if not config.preserve_headings:
            return False

        # Get language-specific heading patterns
        lang_patterns = self.LANGUAGE_HEADING_PATTERNS.get(language_code, self.LANGUAGE_HEADING_PATTERNS["en"])
        
        # Common heading indicators
        common_indicators = [
            r"^(?:[A-Z][a-z]*\s*)+:",  # Capitalized words followed by colon
            r"^[IVX]{1,5}\.?\s+.*$",   # Roman numerals
            r"^\d+\.[\d.]*\s+.*$",      # Numbered headings (1., 1.1., etc.)
            r"^[A-Z\s]{2,}(?::|$)",     # ALL CAPS text
            r"^(?:Section|Chapter|Part|Article)\s+\d+",  # Common document sections
            r"^[A-Z][a-z]+\s+\d+",      # Word + number (Page 1, Section 2)
            r"^[-•*]\s+[A-Z]",          # Bullet points with capital letters
            r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*[:-]"  # Title Case followed by colon or dash
        ]
        
        # Check common patterns first
        for pattern in common_indicators:
            if re.match(pattern, text.strip()):
                return True
        
        # Check language-specific patterns
        for pattern in lang_patterns:
            if re.match(pattern, text.strip()):
                return True
        
        # Check for common heading words
        heading_words = {
            "en": ["summary", "introduction", "conclusion", "overview", "background", "objectives", "methodology", "results", "discussion", "recommendations"],
            "hi": ["सारांश", "परिचय", "निष्कर्ष", "पृष्ठभूमि", "उद्देश्य", "कार्यप्रणाली", "परिणाम", "चर्चा", "सिफारिशें"],
            "fr": ["résumé", "introduction", "conclusion", "aperçu", "contexte", "objectifs", "méthodologie", "résultats", "discussion", "recommandations"],
            "de": ["zusammenfassung", "einleitung", "schlussfolgerung", "überblick", "hintergrund", "ziele", "methodik", "ergebnisse", "diskussion", "empfehlungen"],
            "es": ["resumen", "introducción", "conclusión", "visión general", "antecedentes", "objetivos", "metodología", "resultados", "discusión", "recomendaciones"]
        }
        
        words = text.lower().split()
        if words and words[0] in heading_words.get(language_code, heading_words["en"]):
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
        """Enhanced image redaction with better detection and handling"""
        redacted_images = []
        
        if not tesseract_installed:
            logger.error("Tesseract OCR is not installed. Cannot perform image-based redaction.")
            logger.info("Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
            logger.info("Make sure to check 'Add to PATH' during installation.")
            return []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            
            for img_idx, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    
                    if base_image:
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Convert image bytes to numpy array
                        nparr = np.frombuffer(image_bytes, np.uint8)
                        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if image is not None:
                            # Detect faces using multiple cascades for better accuracy
                            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                            profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
                            
                            if face_cascade.empty() or profile_cascade.empty():
                                logger.warning("Could not load face cascade classifiers")
                                continue
                            
                            # Convert to grayscale for detection
                            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                            
                            # Detect faces (both frontal and profile)
                            faces_frontal = face_cascade.detectMultiScale(gray, 1.3, 5)
                            faces_profile = profile_cascade.detectMultiScale(gray, 1.3, 5)
                            
                            # Combine detected faces
                            faces = list(faces_frontal) + list(faces_profile)
                            
                            if len(faces) > 0:
                                logger.info(f"Found {len(faces)} faces in image on page {page_num + 1}")
                                # Apply redaction to detected faces
                                for (x, y, w, h) in faces:
                                    try:
                                        if config.use_blur:
                                            # Apply Gaussian blur
                                            roi = image[y:y+h, x:x+w]
                                            blurred = cv2.GaussianBlur(roi, (99, 99), 30)
                                            image[y:y+h, x:x+w] = blurred
                                        else:
                                            # Apply solid color redaction
                                            cv2.rectangle(image, (x, y), (x+w, y+h), self.color_map[config.color], -1)
                                    except Exception as e:
                                        logger.error(f"Failed to apply redaction to face: {str(e)}")
                                
                                # Convert back to bytes
                                success, img_bytes = cv2.imencode(f'.{image_ext}', image)
                                if success:
                                    try:
                                        # Replace the image in the PDF
                                        pdf_document.delete_image(xref)
                                        pdf_document.insert_image(
                                            page.get_images(full=True)[img_idx][1],  # Use original rectangle
                                            stream=img_bytes.tobytes(),
                                            filter=base_image.get("filter")
                                        )
                                        
                                        redacted_images.append({
                                            'page': page_num + 1,
                                            'faces_found': len(faces),
                                            'status': 'success'
                                        })
                                        logger.info(f"Successfully redacted faces in image on page {page_num + 1}")
                                    except Exception as e:
                                        logger.error(f"Failed to replace image in PDF: {str(e)}")
                                else:
                                    logger.error("Failed to encode redacted image")
                            
                            # Perform OCR to detect text in images
                            if tesseract_installed:
                                try:
                                    text = pytesseract.image_to_string(image)
                                    if text.strip():
                                        # Search for sensitive information in the text
                                        sensitive_found = False
                                        
                                        # Check for various patterns
                                        patterns = {
                                            'phone': r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
                                            'email': r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                                            'credit_card': r'\b(?:\d{4}[-\s]?){4}\b',
                                            'aadhaar': r'\b\d{4}\s?\d{4}\s?\d{4}\b',
                                            'pan': r'\b[A-Z]{5}\d{4}[A-Z]\b'
                                        }
                                        
                                        for pattern_type, pattern in patterns.items():
                                            if re.search(pattern, text):
                                                sensitive_found = True
                                                logger.info(f"Found sensitive {pattern_type} in image text on page {page_num + 1}")
                                                break
                                        
                                        if sensitive_found:
                                            try:
                                                # Apply full image redaction for sensitive text
                                                if config.use_blur:
                                                    image = cv2.GaussianBlur(image, (99, 99), 30)
                                                else:
                                                    image.fill(self.color_map[config.color][0] * 255)
                                                
                                                # Convert back to bytes and replace
                                                success, img_bytes = cv2.imencode(f'.{image_ext}', image)
                                                if success:
                                                    pdf_document.delete_image(xref)
                                                    pdf_document.insert_image(
                                                        page.get_images(full=True)[img_idx][1],
                                                        stream=img_bytes.tobytes(),
                                                        filter=base_image.get("filter")
                                                    )
                                                    
                                                    redacted_images.append({
                                                        'page': page_num + 1,
                                                        'sensitive_text_found': True,
                                                        'status': 'success'
                                                    })
                                                    logger.info(f"Successfully redacted sensitive text in image on page {page_num + 1}")
                                            except Exception as e:
                                                logger.error(f"Failed to redact sensitive text in image: {str(e)}")
                                except Exception as e:
                                    logger.warning(f"OCR failed for image on page {page_num + 1}: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Failed to process image on page {page_num + 1}: {str(e)}")
                    redacted_images.append({
                        'page': page_num + 1,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        return redacted_images

    def verify_redaction(self, redacted_pdf_path: Path, sensitive_patterns: List[str]) -> bool:
        """Enhanced verification of redaction effectiveness"""
        try:
            # Open the redacted PDF
            pdf_document = fitz.open(str(redacted_pdf_path))
            verification_results = {'success': True, 'issues': []}
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Get both text and words to handle different text extraction methods
                text = page.get_text()
                words = page.get_text("words")
                
                # Check for sensitive patterns in continuous text
                for pattern in sensitive_patterns:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        verification_results['success'] = False
                        verification_results['issues'].append({
                            'page': page_num + 1,
                            'type': 'unredacted_text',
                            'pattern': pattern,
                            'context': text[max(0, match.start()-20):match.end()+20]
                        })
                
                # Check individual words for partial matches
                for word in words:
                    word_text = word[4]  # The actual text content
                    for pattern in sensitive_patterns:
                        if re.search(pattern, word_text):
                            verification_results['success'] = False
                            verification_results['issues'].append({
                                'page': page_num + 1,
                                'type': 'unredacted_word',
                                'pattern': pattern,
                                'text': word_text
                            })
                
                # Check for potentially unredacted images
                image_list = page.get_images(full=True)
                for img_idx, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        
                        if base_image:
                            # Convert image to numpy array
                            image_bytes = base_image["image"]
                            nparr = np.frombuffer(image_bytes, np.uint8)
                            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            
                            if image is not None and tesseract_installed:
                                # Perform OCR on the image
                                text = pytesseract.image_to_string(image)
                                
                                # Check for sensitive information in the OCR text
                                for pattern in sensitive_patterns:
                                    if re.search(pattern, text):
                                        verification_results['success'] = False
                                        verification_results['issues'].append({
                                            'page': page_num + 1,
                                            'type': 'unredacted_image_text',
                                            'pattern': pattern
                                        })
                    except Exception as e:
                        logger.warning(f"Failed to verify image on page {page_num + 1}: {str(e)}")
            
            # Store verification results in the report
            self.report_data['verification_results'] = verification_results
            
            return verification_results['success']
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return False
        finally:
            if 'pdf_document' in locals():
                pdf_document.close()

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
        """Find phone number matches in the page"""
        phone_patterns = [
            r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # US/Canada
            r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
            r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",
            r"\b(?:\+\d{1,3}[-.\s]?)?\d{1,4}[-.\s]?\d{2,4}[-.\s]?\d{4}\b",  # International
            r"\b(?:\+91[-\s]?)?[6789]\d{9}\b",  # Indian mobile
            r"\b0\d{2,4}[-\s]?\d{6,8}\b"  # Indian landline
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in phone_patterns:
            found = re.finditer(pattern, text)
            for match in found:
                if not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    def find_email_matches(self, page, page_num):
        """Find email address matches in the page"""
        email_patterns = [
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
            r"\b[a-zA-Z0-9._%+-]+(?:@|\[at\])[a-zA-Z0-9.-]+(?:\.|\[dot\])[a-zA-Z]{2,}\b"  # Handle obfuscated emails
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in email_patterns:
            found = re.finditer(pattern, text)
            for match in found:
                if not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    def find_credit_card_matches(self, page, page_num):
        """Find credit card number matches in the page"""
        cc_patterns = [
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",  # Major card types
            r"\b(?:\d{4}[-\s]?){4}\b",  # Formatted with spaces/dashes
            r"\b\d{16}\b"  # Raw 16 digits
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in cc_patterns:
            found = re.finditer(pattern, text)
            for match in found:
                # Validate using Luhn algorithm
                card_number = re.sub(r'[-\s]', '', match.group())
                if self.is_valid_credit_card(card_number) and not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    @staticmethod
    def is_valid_credit_card(card_number):
        """Validate credit card number using Luhn algorithm"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10 == 0

    def find_cvv_matches(self, page, page_num):
        """Find CVV/CVC code matches in the page"""
        cvv_patterns = [
            r"\b(?:CVV|CVC|CVV2|CID)[\s:]*\d{3,4}\b",
            r"\b(?:security code|card code)[\s:]*\d{3,4}\b",
            r"\b\d{3,4}(?=\s*(?:CVV|CVC|CVV2|CID))\b"
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in cvv_patterns:
            found = re.finditer(pattern, text)
            for match in found:
                if not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    def find_cc_expiration_matches(self, page, page_num):
        """Find credit card expiration date matches in the page"""
        expiration_patterns = [
            r"\b(?:0[1-9]|1[0-2])[-/](?:[0-9]{2}|2[0-9]{3})\b",  # MM/YY or MM/YYYY
            r"\b(?:0[1-9]|1[0-2])[-/](?:[0-9]{2})\b",  # MM/YY
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[,\s]+\d{4}\b",  # Month YYYY
            r"\b(?:expir(?:y|ation)|valid thru|good thru)[\s:]*(?:0[1-9]|1[0-2])[-/](?:[0-9]{2}|2[0-9]{3})\b"  # With labels
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in expiration_patterns:
            found = re.finditer(pattern, text, re.IGNORECASE)
            for match in found:
                if not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    def find_aadhaar_matches(self, page, page_num):
        """Find Aadhaar number matches in the page"""
        aadhaar_patterns = [
            r"\b\d{4}\s?\d{4}\s?\d{4}\b",
            r"\b(?:Aadhaar|आधार)[\s:]*\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            r"\bUID[\s:]*\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in aadhaar_patterns:
            found = re.finditer(pattern, text)
            for match in found:
                aadhaar = re.sub(r'[-\s]', '', match.group())
                if self.is_valid_aadhaar(aadhaar) and not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    def find_pan_matches(self, page, page_num):
        """Find PAN card number matches in the page"""
        pan_patterns = [
            r"\b[A-Z]{5}\d{4}[A-Z]\b",
            r"\b(?:PAN|Permanent Account Number|पैन)[\s:]*[A-Z]{5}\d{4}[A-Z]\b"
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in pan_patterns:
            found = re.finditer(pattern, text)
            for match in found:
                pan = re.sub(r'[-\s]', '', match.group())
                if self.is_valid_pan(pan) and not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    @staticmethod
    def is_valid_aadhaar(aadhaar):
        """Validate Aadhaar number using Verhoeff algorithm"""
        # Remove any spaces or special characters
        aadhaar = re.sub(r'[-\s]', '', aadhaar)
        
        if not re.match(r'^\d{12}$', aadhaar):
            return False
            
        # Verhoeff algorithm multiplication table
        mult = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
        ]
        
        # Verhoeff algorithm permutation table
        perm = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
            [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
            [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
            [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
            [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
            [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
            [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
        ]
        
        # Verhoeff algorithm inverse table
        inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
        
        # Calculate checksum
        check = 0
        for i, digit in enumerate(reversed(aadhaar)):
            check = mult[check][perm[i % 8][int(digit)]]
        
        return check == 0

    @staticmethod
    def is_valid_pan(pan):
        """Validate PAN card number format"""
        # Remove any spaces or special characters
        pan = re.sub(r'[-\s]', '', pan.upper())
        
        if not re.match(r'^[A-Z]{5}\d{4}[A-Z]$', pan):
            return False
            
        # Check if first character is valid
        if pan[0] not in 'ABCDEFGHIJKLKLMNOPQRSTUVWXYZ':
            return False
            
        # Check if fourth character is valid
        if pan[3] not in 'ABCFGHLJPT':
            return False
            
        # Check if fifth character is valid
        if pan[4] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            return False
            
        return True

    def find_iban_matches(self, page, page_num):
        """Find IBAN matches in the page"""
        iban_patterns = [
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b",
            r"\b(?:IBAN|International Bank Account Number)[\s:]*[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b"
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in iban_patterns:
            found = re.finditer(pattern, text)
            for match in found:
                iban = re.sub(r'\s+', '', match.group())
                if self.is_valid_iban(iban) and not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    def find_bic_matches(self, page, page_num):
        """Find BIC/SWIFT code matches in the page"""
        bic_patterns = [
            r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",
            r"\b(?:BIC|SWIFT)[\s:]*[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"
        ]
        
        matches = []
        text = page.get_text()
        
        for pattern in bic_patterns:
            found = re.finditer(pattern, text)
            for match in found:
                if self.is_valid_bic(match.group()) and not self.is_heading(text[max(0, match.start()-50):match.end()+50], self.config):
                    matches.append({
                        'text': match.group(),
                        'bbox': page.search_for(match.group()),
                        'page': page_num
                    })
        
        return matches

    @staticmethod
    def is_valid_iban(iban):
        """Validate IBAN using the MOD-97 algorithm"""
        # Remove spaces and convert to uppercase
        iban = re.sub(r'\s+', '', iban.upper())
        
        if not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{4,}$', iban):
            return False
        
        # Move first 4 characters to end and convert letters to numbers
        iban = iban[4:] + iban[:4]
        iban_digits = ''
        for char in iban:
            if char.isdigit():
                iban_digits += char
            else:
                iban_digits += str(ord(char) - ord('A') + 10)
        
        # Check if MOD-97 equals 1
        return int(iban_digits) % 97 == 1

    @staticmethod
    def is_valid_bic(bic):
        """Validate BIC/SWIFT code format"""
        bic = re.sub(r'\s+', '', bic.upper())
        
        if not re.match(r'^[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?$', bic):
            return False
        
        # Check if bank code part (first 4 chars) contains only letters
        if not bic[:4].isalpha():
            return False
        
        # Check if country code (chars 5-6) is valid
        if not bic[4:6].isalpha():
            return False
        
        return True

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
