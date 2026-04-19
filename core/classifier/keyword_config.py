"""
core/classifier/keyword_config.py
Weighted keyword signals for document classification.
All weights are tunable — do not hard-code them in logic.
"""

KEYWORD_SIGNALS = {
    "aadhaar": {
        "primary": [
            ("aadhaar", 30),
            ("uidai", 25),
            ("unique identification authority", 20),
            ("aadhaar number", 30),
            ("आधार", 25),
            ("ಆಧಾರ್", 25),
            ("ஆதார்", 25),
        ],
        "secondary": [
            ("government of india", 10),
            ("dob", 5),
            ("address", 5),
            ("male", 3),
            ("female", 3),
            ("enrolment", 8),
            ("enrollment", 8),
        ],
        "pattern": [
            (r"\d{4}\s\d{4}\s\d{4}", 40),   # 12-digit Aadhaar
            (r"\d{4}-\d{4}-\d{4}", 40),       # hyphen variant
            (r"\d{12}", 30),                   # no-separator variant
        ],
    },
    "pan": {
        "primary": [
            ("permanent account number", 35),
            ("income tax department", 25),
            ("income tax", 20),
            ("pan card", 20),
            ("आयकर विभाग", 25),
            ("आयकर", 20),
        ],
        "secondary": [
            ("government of india", 10),
            ("father", 5),
            ("date of birth", 5),
            ("signature", 5),
        ],
        "pattern": [
            (r"[A-Z]{5}[0-9]{4}[A-Z]{1}", 45),  # PAN format
        ],
    },
    "sslc": {
        "primary": [
            ("sslc", 35),
            ("secondary school leaving certificate", 35),
            ("secondary school", 25),
            ("board of secondary education", 25),
            ("karnataka secondary education examination board", 35),
            ("kseeb", 30),
            ("ಎಸ್.ಎಸ್.ಎಲ್.ಸಿ", 30),
        ],
        "secondary": [
            ("register number", 10),
            ("marks", 8),
            ("total marks", 10),
            ("pass", 5),
            ("fail", 5),
            ("percentage", 8),
            ("class", 5),
            ("mathematics", 5),
            ("science", 5),
            ("social science", 5),
        ],
        "pattern": [
            (r"\d{2}-\d{2}-\d{6}", 20),       # Register number
            (r"[A-Z]{3}\d{6}", 15),             # Alternate register formats
        ],
    },
    "voter_id": {
        "primary": [
            ("election commission of india", 30),
            ("electors photo identity card", 35),
            ("epic", 20),
            ("voter id", 25),
        ],
        "secondary": [
            ("part no", 5),
            ("serial no", 5),
            ("constituency", 8),
        ],
        "pattern": [
            (r"[A-Z]{3}[0-9]{7}", 35),
        ],
    },
    "driving_license": {
        "primary": [
            ("driving licence", 35),
            ("driving license", 35),
            ("transport department", 25),
            ("dl no", 20),
        ],
        "secondary": [
            ("valid upto", 8),
            ("cov", 5),
            ("blood group", 5),
        ],
        "pattern": [
            (r"[A-Z]{2}\d{13}", 35),
            (r"[A-Z]{2}-\d{2}-\d{4}-\d{7}", 30),
        ],
    },
}

# Fields that MUST be present in a genuine document of each type
REQUIRED_FIELDS = {
    "aadhaar": ["name", "dob", "number"],
    "pan": ["name", "number", "dob"],
    "sslc": ["name", "register_number", "marks"],
    "voter_id": ["name", "epic_number"],
    "driving_license": ["name", "dl_number"],
}

# Minimum score to even attempt classification
MIN_CLASSIFICATION_SCORE = 30
