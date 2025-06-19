from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from enum import Enum

# Custom validator functions for flexible enum handling
def normalize_roast_level(value):
    """Normalize roast level to standard format"""
    if not value:
        return None
    value = str(value).lower().strip()
    
    # Map common variations to standard values
    roast_mapping = {
        'light': 'light',
        'lite': 'light',
        'blonde': 'light',
        'cinnamon': 'light',
        'medium-light': 'medium-light',
        'medium light': 'medium-light',
        'city': 'medium-light',
        'medium': 'medium',
        'med': 'medium',
        'city+': 'medium',
        'full city': 'medium',
        'medium-dark': 'medium-dark',
        'medium dark': 'medium-dark',
        'full city+': 'medium-dark',
        'vienna': 'medium-dark',
        'dark': 'dark',
        'french': 'dark',
        'italian': 'dark',
        'espresso': 'dark'
    }
    
    return roast_mapping.get(value, value)  # Return normalized or original

def normalize_grind_type(value):
    """Normalize grind type to standard format"""
    if not value:
        return None
    value = str(value).lower().strip()
    
    grind_mapping = {
        'whole': 'whole',
        'whole bean': 'whole',
        'whole beans': 'whole',
        'bean': 'whole',
        'beans': 'whole',
        'ground': 'ground',
        'pre-ground': 'ground',
        'preground': 'ground'
    }
    
    return grind_mapping.get(value, value)

def normalize_process_type(value):
    """Normalize process type to standard format"""
    if not value:
        return None
    value = str(value).lower().strip()
    
    process_mapping = {
        'natural': 'natural',
        'dry': 'natural',
        'sun-dried': 'natural',
        'washed': 'washed',
        'wet': 'washed',
        'fully washed': 'washed',
        'honey': 'honey',
        'semi-washed': 'honey',
        'pulped natural': 'pulped_natural',
        'pulped-natural': 'pulped_natural',
        'wet hulled': 'wet_hulled',
        'wet-hulled': 'wet_hulled',
        'giling basah': 'wet_hulled'
    }
    
    return process_mapping.get(value, value)

def normalize_bean_type(value):
    """Normalize bean type to standard format"""
    if not value:
        return None
    value = str(value).lower().strip()
    
    bean_mapping = {
        'arabica': 'arabica',
        'coffea arabica': 'arabica',
        'robusta': 'robusta',
        'coffea robusta': 'robusta',
        'coffea canephora': 'robusta',
        'liberica': 'liberica',
        'coffea liberica': 'liberica',
        'excelsa': 'excelsa',
        'coffea excelsa': 'excelsa'
    }
    
    return bean_mapping.get(value, value)

def normalize_brew_type(value):
    """Normalize brew type to standard format"""
    if not value:
        return None
    value = str(value).lower().strip()
    
    brew_mapping = {
        'espresso': 'espresso',
        'drip': 'drip',
        'filter': 'drip',
        'auto drip': 'drip',
        'french press': 'french_press',
        'french-press': 'french_press',
        'press pot': 'french_press',
        'pour over': 'pour_over',
        'pour-over': 'pour_over',
        'v60': 'pour_over',
        'chemex': 'pour_over',
        'cold brew': 'cold_brew',
        'cold-brew': 'cold_brew',
        'aeropress': 'aeropress',
        'aero press': 'aeropress'
    }
    
    return brew_mapping.get(value, value)

class GrindType(str, Enum):
    WHOLE = "whole"
    GROUND = "ground"

class RoastLevel(str, Enum):
    LIGHT = "light"
    MEDIUM_LIGHT = "medium-light"
    MEDIUM = "medium"
    MEDIUM_DARK = "medium-dark"
    DARK = "dark"

class ProcessType(str, Enum):
    NATURAL = "natural"
    WASHED = "washed"
    HONEY = "honey"
    PULPED_NATURAL = "pulped_natural"
    WET_HULLED = "wet_hulled"

class BeanType(str, Enum):
    ARABICA = "arabica"
    ROBUSTA = "robusta"
    LIBERICA = "liberica"
    EXCELSA = "excelsa"

class BrewType(str, Enum):
    ESPRESSO = "espresso"
    DRIP = "drip"
    FRENCH_PRESS = "french_press"
    POUR_OVER = "pour_over"
    COLD_BREW = "cold_brew"
    AEROPRESS = "aeropress"

class BeanInfo(BaseModel):
    """Level 1: General bean information"""
    name: Optional[str] = Field(None, description="Name of the coffee bean")
    weight: Optional[str] = Field(None, description="Weight of the package (e.g., '12oz', '340g')")
    price: Optional[str] = Field(None, description="Price of the coffee")
    producer: Optional[str] = Field(None, description="Bean proprietor/producer")
    region: Optional[str] = Field(None, description="Coffee growing region (country/area)")
    roast_level: Optional[Union[RoastLevel, str]] = Field(None, description="Roast level")
    flavor_notes: Optional[List[str]] = Field(None, description="Flavor notes/tasting notes")
    grind_type: Optional[Union[GrindType, str]] = Field(None, description="Grind type (whole/ground)")
    
    @field_validator('roast_level', mode='before')
    @classmethod
    def validate_roast_level(cls, v):
        if v is None:
            return None
        normalized = normalize_roast_level(v)
        # Return normalized value if it matches enum, otherwise return as string
        try:
            return RoastLevel(normalized)
        except ValueError:
            return normalized
    
    @field_validator('grind_type', mode='before')
    @classmethod
    def validate_grind_type(cls, v):
        if v is None:
            return None
        normalized = normalize_grind_type(v)
        try:
            return GrindType(normalized)
        except ValueError:
            return normalized

class SpecialtyBeanInfo(BaseModel):
    """Level 2: Specialty bean information"""
    farm: Optional[str] = Field(None, description="Farm name")
    altitude: Optional[str] = Field(None, description="Altitude in masl (meters above sea level)")
    process: Optional[Union[ProcessType, str]] = Field(None, description="Processing method")
    agtron_roast_level: Optional[str] = Field(None, description="Agtron roast level number")
    suitable_brew_types: Optional[List[Union[BrewType, str]]] = Field(None, description="Suitable brewing methods")
    bean_type: Optional[Union[BeanType, str]] = Field(None, description="Type of coffee bean")
    variety: Optional[str] = Field(None, description="Coffee variety/cultivar")
    
    @field_validator('process', mode='before')
    @classmethod
    def validate_process(cls, v):
        if v is None:
            return None
        normalized = normalize_process_type(v)
        try:
            return ProcessType(normalized)
        except ValueError:
            return normalized
    
    @field_validator('bean_type', mode='before')
    @classmethod
    def validate_bean_type(cls, v):
        if v is None:
            return None
        normalized = normalize_bean_type(v)
        try:
            return BeanType(normalized)
        except ValueError:
            return normalized
    
    @field_validator('suitable_brew_types', mode='before')
    @classmethod
    def validate_brew_types(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        
        normalized_list = []
        for brew_type in v:
            if brew_type is None:
                continue
            normalized = normalize_brew_type(brew_type)
            try:
                normalized_list.append(BrewType(normalized))
            except ValueError:
                normalized_list.append(normalized)
        
        return normalized_list if normalized_list else None

class CoffeeBean(BaseModel):
    """Complete coffee bean information"""
    basic_info: BeanInfo
    specialty_info: Optional[SpecialtyBeanInfo] = None
    raw_html: Optional[str] = Field(None, description="Original HTML content for reference")
    source_url: Optional[str] = Field(None, description="URL where this information was found")

class MenuItem(BaseModel):
    """Coffee menu item/beverage"""
    name: str = Field(..., description="Name of the coffee beverage")
    description: Optional[str] = Field(None, description="Description of the beverage")
    price: Optional[str] = Field(None, description="Price of the beverage")
    sizes: Optional[List[str]] = Field(None, description="Available sizes")
    category: Optional[str] = Field(None, description="Category (e.g., espresso, specialty drinks)")
    ingredients: Optional[List[str]] = Field(None, description="Main ingredients")

class CafeMenu(BaseModel):
    """Complete cafe menu information"""
    items: List[MenuItem]
    cafe_name: Optional[str] = Field(None, description="Name of the cafe")
    source_url: Optional[str] = Field(None, description="URL where this menu was found")

class ScrapedData(BaseModel):
    """Complete scraped data from a cafe website"""
    cafe_name: Optional[str] = None
    base_url: str
    coffee_beans: List[CoffeeBean] = []
    menu: Optional[CafeMenu] = None
    all_urls_crawled: List[str] = []
    timestamp: Optional[str] = None 