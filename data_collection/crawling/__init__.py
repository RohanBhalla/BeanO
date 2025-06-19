"""
Cafe Web Scraper Package

A robust web crawler and scraper system designed specifically for coffee shop 
and cafe websites. Uses intelligent crawling combined with LLM processing to 
extract structured information about coffee beans and menu items.

Main Components:
- WebCrawler: Discovers and crawls all pages on a cafe website
- LLMProcessor: Uses LLM to extract structured data from HTML content  
- CafeScraper: Main orchestrator that combines crawling and processing
- Models: Pydantic models for structured data representation

Usage:
    from data_collection.crawling import quick_scrape, CafeScraper
    
    # Quick scrape with default settings
    result = quick_scrape("https://example-cafe.com")
    
    # Advanced usage with custom configuration
    scraper = CafeScraper(llm_config)
    result = scraper.scrape_cafe_website("https://example-cafe.com")
"""

from .data_models.models import (
    BeanInfo, SpecialtyBeanInfo, CoffeeBean,
    MenuItem, CafeMenu, ScrapedData,
    GrindType, RoastLevel, ProcessType, BeanType, BrewType
)

from .web_crawler import WebCrawler, CrawlConfig, create_coffee_crawler

from ..processing.llm_processor import LLMProcessor, LLMConfig

from .cafe_scraper import CafeScraper, quick_scrape

__version__ = "1.0.0"
__author__ = "Cafe Scraper Team"

__all__ = [
    # Main classes
    "CafeScraper",
    "WebCrawler", 
    "LLMProcessor",
    
    # Configuration classes
    "CrawlConfig",
    "LLMConfig",
    
    # Data models
    "BeanInfo",
    "SpecialtyBeanInfo", 
    "CoffeeBean",
    "MenuItem",
    "CafeMenu",
    "ScrapedData",
    
    # Enums
    "GrindType",
    "RoastLevel", 
    "ProcessType",
    "BeanType",
    "BrewType",
    
    # Utility functions
    "quick_scrape",
    "create_coffee_crawler"
] 