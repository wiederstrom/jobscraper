"""
Constants for job scraper application
"""

from typing import List

# Norwegian month names for deadline parsing
NORWEGIAN_MONTHS = {
    'januar': 1,
    'februar': 2,
    'mars': 3,
    'april': 4,
    'mai': 5,
    'juni': 6,
    'juli': 7,
    'august': 8,
    'september': 9,
    'oktober': 10,
    'november': 11,
    'desember': 12
}

# Job sources
SOURCE_FINN = "FINN"
SOURCE_NAV = "NAV"

# Job statuses
STATUS_ACTIVE = "ACTIVE"
STATUS_INACTIVE = "INACTIVE"
STATUS_EXPIRED = "EXPIRED"
