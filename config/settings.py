class Config:
    # Amazon settings
    BASE_URL = "https://www.amazon.com"
    
    # Request settings
    MIN_DELAY = 2  # Minimum delay between requests
    MAX_DELAY = 5  # Maximum delay between requests
    
    # Scraping settings
    MAX_PAGES = 5  # Maximum pages to scrape per search
    
    # Scoring weights
    BSR_WEIGHT = 0.4
    REVIEWS_WEIGHT = 0.3
    MARGIN_WEIGHT = 0.3
    
    # FBA fee estimation
    BASE_FBA_FEE = 5.0
    FBA_PERCENTAGE = 0.15
    REFERRAL_FEE_PERCENTAGE = 0.15
    
    # Rate limiting
    REQUESTS_PER_MINUTE = 20