from enum import Enum

class CrisisCategory(str, Enum):
    ILLEGAL_EVICTION = "illegal_eviction"               
    DOMESTIC_VIOLENCE = "domestic_violence"             
    SENIOR_CITIZEN_NEGLECT = "senior_citizen_neglect"   
    NATURAL_DISASTER = "natural_disaster"               
    LAWFUL_EVICTION = "lawful_eviction"                 
    UNCLEAR = "unclear"

class DocumentType(str, Enum):
    EVICTION_NOTICE = "eviction_notice"
    COURT_ORDER = "court_order"               
    PROPERTY_DEED = "property_deed"           
    DIR_OR_FIR = "dir_or_fir"                 
    RENT_AGREEMENT = "rent_agreement"
    UNKNOWN = "unknown"

class UrgencyLevel(str, Enum):
    CRITICAL = "critical" # User is currently locked out / on the street tonight
    HIGH = "high"         # Eviction happening in < 24 hours / Utilities cut
    MEDIUM = "medium"     # Eviction notice received, but has a few days
    LOW = "low"           # General legal query

