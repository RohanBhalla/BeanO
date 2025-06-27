# To run this code you need to install the following dependencies:
# pip install google-genai beautifulsoup4

import base64
import os
import json
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from google import genai
from google.genai import types
from bs4 import BeautifulSoup
from dotenv import load_dotenv
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiHTMLProcessor:
    """Process HTML files using Gemini to extract coffee bean information"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini processor
        
        Args:
            api_key: Gemini API key (defaults to environment variable)
        """
        # Load environment variables from .env file
        load_dotenv()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash-lite-preview-06-17"
        
        # Create processed_docs directory
        self.output_dir = Path(__file__).parent / "processed_docs"
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized Gemini processor. Output directory: {self.output_dir}")
    
    def extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content while preserving product descriptions"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # First, try to extract structured product data and descriptions
            structured_content = []
            
            # Extract meta descriptions which often contain product descriptions
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                structured_content.append(f"META DESCRIPTION: {meta_desc.get('content')}")
            
            # Extract OpenGraph descriptions
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                structured_content.append(f"OG DESCRIPTION: {og_desc.get('content')}")
            
            # Extract Twitter card descriptions
            twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
            if twitter_desc and twitter_desc.get('content'):
                structured_content.append(f"TWITTER DESCRIPTION: {twitter_desc.get('content')}")
            
            # Look for product description sections in common HTML patterns
            description_selectors = [
                '[class*="description"]',
                '[class*="product-description"]', 
                '[class*="product-details"]',
                '[class*="product-info"]',
                '[id*="description"]',
                '.prose p', # Common for product content
                '[data-product-description]'
            ]
            
            for selector in description_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if len(text) > 50 and any(keyword in text.lower() for keyword in ['flavor', 'taste', 'blend', 'roast', 'origin', 'notes', 'brew', 'coffee']):
                        structured_content.append(f"PRODUCT DESCRIPTION: {text}")
            
            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            full_text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Combine structured content with full text
            final_text = '\n\n'.join(structured_content) + '\n\nFULL PAGE CONTENT:\n' + full_text
            
            # Limit text length to avoid token limits
            max_chars = 50000  # Approximate limit for Gemini
            if len(final_text) > max_chars:
                # Prioritize keeping the structured descriptions
                structured_part = '\n\n'.join(structured_content)
                remaining_chars = max_chars - len(structured_part) - 100
                if remaining_chars > 0:
                    final_text = structured_part + '\n\nFULL PAGE CONTENT:\n' + full_text[:remaining_chars] + "..."
                else:
                    final_text = structured_part + "..."
                logger.warning(f"Text truncated to {max_chars} characters")
            
            return final_text
        
        except Exception as e:
            logger.error(f"Error extracting text from HTML: {e}")
            return ""
    
    def create_prompt(self, text_content: str) -> str:
        """Create the prompt for Gemini with the extracted text"""
        prompt = f"""
Extract coffee bean product data from the HTML. Return only actual products for sale.

CRITICAL: You MUST extract the product description. Look for:
- Meta descriptions (META DESCRIPTION, OG DESCRIPTION, TWITTER DESCRIPTION)
- Product description sections (PRODUCT DESCRIPTION)
- Marketing copy describing the coffee's characteristics
- Flavor profiles and tasting notes descriptions
- Origin stories and brewing recommendations
- Any text that describes what the coffee tastes like or its characteristics

Required fields (ALL MUST BE EXTRACTED):
- name: Product name
- weight: Package size (e.g., "12oz", "340g") 
- price: Listed price (number only)
- currency: Currency of the price
- producer: Roaster/brand name
- region: Origin country/area
- roast_level: LIGHT/MEDIUM_LIGHT/MEDIUM/MEDIUM_DARK/DARK/EXTRA_DARK
- flavor_notes: Array of tasting notes
- grind_type: WHOLE/COARSE/MEDIUM/FINE/etc.
- description: **REQUIRED** - Detailed product description. This should be a comprehensive description including flavor profile, characteristics, brewing notes, origin story, or marketing copy. Look in meta tags, product sections, and descriptive text. If multiple descriptions exist, combine them into one comprehensive description.

Optional specialty fields (when available):
- farm: Farm name
- altitude: Elevation in masl
- process: Processing method (natural, washed, honey, etc.)
- agtron_roast_level: Agtron number/measurement
- suitable_brew_types: Recommended brewing methods
- bean_type: Coffee species (Arabica, Robusta, Liberica, Excelsa)
- variety: Coffee variety/cultivar

DESCRIPTION EXTRACTION EXAMPLES:
- "A perennial filter classic with flavors of creamy cocoa, sweet toffee and rich dried fruits"
- "This Ethiopian coffee features bright citrus notes with a floral aroma and honey sweetness"
- "Medium roast blend perfect for espresso with chocolate and caramel undertones"

IMPORTANT: 
- Every product MUST have a description - this is not optional
- If you find meta descriptions, product descriptions, or marketing copy, use them
- Combine multiple description sources if needed
- Skip navigation, headers, footers, and non-product content
- Return empty array if no coffee products found

Website content:
{text_content}
"""
        return prompt
    
    def create_menu_prompt(self, text_content: str) -> str:
        """Create the prompt for Gemini to extract menu items from cafe content"""
        prompt = f"""
Please analyze the following text extracted from a coffee shop/cafe website and extract ALL menu items available.

Look for menu items including:
- Coffee drinks (espresso, latte, cappuccino, americano, etc.)
- Tea beverages (hot tea, iced tea, specialty teas, etc.)
- Cold beverages (iced coffee, cold brew, smoothies, juices, etc.)
- Hot beverages (hot chocolate, chai, etc.)
- Food items (pastries, sandwiches, salads, soups, etc.)
- Desserts (cakes, cookies, muffins, etc.)
- Breakfast items
- Lunch items
- Snacks

For each menu item, extract:
- Item name
- Price (if available)
- Description (if available)
- Category/type of item
- Size options (if available)
- Any special ingredients or dietary notes

Only extract actual menu items that customers can order. Ignore general website content, navigation, headers, footers, promotional text, etc.

If no menu items are found, return an empty array.

Website content:
{text_content}
"""
        return prompt
    
    def validate_extraction_results(self, coffee_beans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted coffee beans and ensure descriptions are present"""
        validated_beans = []
        
        for i, bean in enumerate(coffee_beans):
            # Check if description exists and is meaningful
            description = bean.get('description', '').strip()
            
            if not description:
                logger.warning(f"Bean {i+1} '{bean.get('name', 'Unknown')}' is missing description - this is required")
                # Don't skip the bean, but log the issue
                bean['description'] = "Description not available in source content"
            elif len(description) < 20:
                logger.warning(f"Bean {i+1} '{bean.get('name', 'Unknown')}' has very short description: '{description}'")
            else:
                logger.info(f"Bean {i+1} '{bean.get('name', 'Unknown')}' has description of {len(description)} characters")
            
            validated_beans.append(bean)
        
        return validated_beans

    def process_with_gemini(self, text_content: str) -> List[Dict[str, Any]]:
        """Process text content with Gemini and return structured data"""
        try:
            prompt = self.create_prompt(text_content)
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=0.3,  # Slightly increased for more comprehensive extraction
                thinking_config=types.ThinkingConfig(
                    thinking_budget=2000,  # Increased thinking budget
                ),
                response_mime_type="application/json",
                response_schema=genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    description="A list of coffee bean information objects, including both general and specialty details.",
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        description="Combined Bean Information: Level 1 (General) and Level 2 (Specialty)",
                        properties={
                            "name": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Name of the coffee bean",
                            ),
                            "weight": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Weight of the package (e.g., '12oz', '340g')",
                            ),
                            "price": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                                description="Price of the coffee",
                            ),
                            "currency": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Currency of the price",
                                enum=["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SEK", "NOK", "DKK", "INR", "other"],
                            ),
                            "description": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="REQUIRED: Comprehensive product description including flavor profile, characteristics, brewing notes, origin story, or marketing copy. Must be extracted from meta tags, product sections, or descriptive text.",
                            ),
                            "producer": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Bean proprietor/producer or farm where the coffee is grown",
                            ),
                            "region": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Coffee growing region (country/area)",
                            ),
                            "roast_level": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Roast level",
                                enum=["LIGHT", "MEDIUM_LIGHT", "MEDIUM", "MEDIUM_DARK", "DARK", "EXTRA_DARK", "NO_PREFERENCE"],
                            ),
                            "flavor_notes": genai.types.Schema(
                                type=genai.types.Type.ARRAY,
                                description="Flavor notes/tasting notes",
                                items=genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                ),
                            ),
                            "grind_type": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Grind type (whole/ground)",
                                enum=["WHOLE", "EXTRA_COARSE", "COARSE", "MEDIUM_COARSE", "MEDIUM", "MEDIUM_FINE", "FINE", "EXTRA_FINE", "TURKISH"],
                            ),
                            "farm": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Farm name",
                            ),
                            "altitude": genai.types.Schema(
                                type=genai.types.Type.INTEGER,
                                description="Altitude in masl (meters above sea level)",
                            ),
                            "process": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Processing method"
                            ),
                            "agtron_roast_level": genai.types.Schema(
                                type=genai.types.Type.INTEGER,
                                description="Agtron roast level number",
                            ),
                            "suitable_brew_types": genai.types.Schema(
                                type=genai.types.Type.ARRAY,
                                description="Suitable brewing methods",
                                items=genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                    enum=["DRIP_FILTER", "ESPRESSO", "POUR_OVER", "FRENCH_PRESS", "COLD_BREW", "AEROPRESS", "MOKA_POT", "SIPHON", "OTHER"],
                                ),
                            ),
                            "bean_type": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Type of coffee bean (e.g., Arabica, Robusta, Liberica, Excelsa)",
                                enum=["ARABICA", "ROBUSTA", "LIBERICA", "EXCELSA"],
                            ),
                            "variety": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Specific coffee variety/cultivar (e.g., Bourbon, Typica, Geisha) within the bean type.",
                            ),
                        },
                        required=["name", "price", "description"],  # Making description required
                    ),
                ),
            )
            
            # Collect the full response
            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            ):
                response_text += chunk.text
            
            # Parse JSON response
            try:
                result = json.loads(response_text)
                if isinstance(result, list):
                    # Validate the results
                    validated_result = self.validate_extraction_results(result)
                    return validated_result
                else:
                    return []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text: {response_text}")
                return []
                
        except Exception as e:
            logger.error(f"Error processing with Gemini: {e}")
            return []
    
    def process_menu_with_gemini(self, text_content: str) -> List[Dict[str, Any]]:
        """Process text content with Gemini to extract menu items and return structured data"""
        try:
            prompt = self.create_menu_prompt(text_content)
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=0.25,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=-1,
                ),
                response_mime_type="application/json",
                response_schema=genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    description="A list of cafe menu items",
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        description="Menu item information",
                        properties={
                            "name": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Name of the menu item",
                            ),
                            "price": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Price of the item (if available)",
                            ),
                            "description": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Description of the menu item (if available)",
                            ),
                            "category": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Category of the menu item",
                                enum=["COFFEE", "TEA", "COLD_BEVERAGE", "HOT_BEVERAGE", "FOOD", "DESSERT", "BREAKFAST", "LUNCH", "SNACK", "OTHER"],
                            ),
                            "size_options": genai.types.Schema(
                                type=genai.types.Type.ARRAY,
                                description="Available size options (if any)",
                                items=genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                ),
                            ),
                            "dietary_notes": genai.types.Schema(
                                type=genai.types.Type.ARRAY,
                                description="Dietary information or special ingredients",
                                items=genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                ),
                            ),
                        },
                        required=["name", "category"],
                    ),
                ),
            )
            
            # Collect the full response
            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            ):
                response_text += chunk.text
            
            # Parse JSON response
            try:
                result = json.loads(response_text)
                return result if isinstance(result, list) else []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text: {response_text}")
                return []
                
        except Exception as e:
            logger.error(f"Error processing menu with Gemini: {e}")
            return []
    
    def extract_menu_items_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract menu items from HTML content using Gemini
        
        Args:
            html_content: Raw HTML content from a cafe website
            
        Returns:
            List of dictionaries containing menu item information
        """
        logger.info("Extracting menu items from HTML content")
        
        try:
            # Extract text from HTML
            text_content = self.extract_text_from_html(html_content)
            
            if not text_content.strip():
                logger.warning("No text content extracted from HTML")
                return []
            
            # Process with Gemini to extract menu items
            menu_items = self.process_menu_with_gemini(text_content)
            
            logger.info(f"Extracted {len(menu_items)} menu items from HTML content")
            return menu_items
            
        except Exception as e:
            logger.error(f"Error extracting menu items from HTML: {e}")
            return []

    def process_html_file(self, html_file_path: Path) -> Dict[str, Any]:
        """Process a single HTML file and return results"""
        logger.info(f"Processing file: {html_file_path.name}")
        
        try:
            # Read HTML file
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract text
            text_content = self.extract_text_from_html(html_content)
            
            if not text_content.strip():
                logger.warning(f"No text content extracted from {html_file_path.name}")
                return {
                    'source_file': html_file_path.name,
                    'processed_at': datetime.now().isoformat(),
                    'coffee_beans': [],
                    'error': 'No text content extracted'
                }
            
            # Process with Gemini
            coffee_beans = self.process_with_gemini(text_content)
            
            result = {
                'source_file': html_file_path.name,
                'processed_at': datetime.now().isoformat(),
                'coffee_beans': coffee_beans,
                'beans_found': len(coffee_beans)
            }
            
            logger.info(f"Found {len(coffee_beans)} coffee bean products in {html_file_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing file {html_file_path.name}: {e}")
            return {
                'source_file': html_file_path.name,
                'processed_at': datetime.now().isoformat(),
                'coffee_beans': [],
                'error': str(e)
            }
    
    def process_directory(self, input_dir: str) -> Dict[str, Any]:
        """Process all HTML files in a directory"""
        input_path = Path(input_dir)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Find all HTML files
        html_files = list(input_path.glob("*.html"))
        
        if not html_files:
            logger.warning(f"No HTML files found in {input_dir}")
            return {
                'input_directory': str(input_path),
                'processed_at': datetime.now().isoformat(),
                'files_processed': 0,
                'total_beans_found': 0,
                'results': []
            }
        
        logger.info(f"Found {len(html_files)} HTML files to process")
        
        results = []
        total_beans = 0
        
        for html_file in html_files:
            result = self.process_html_file(html_file)
            results.append(result)
            total_beans += result.get('beans_found', 0)
            
            # Save individual result
            output_file = self.output_dir / f"{html_file.stem}_processed.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Create summary
        summary = {
            'input_directory': str(input_path),
            'processed_at': datetime.now().isoformat(),
            'files_processed': len(html_files),
            'total_beans_found': total_beans,
            'results': results
        }
        
        # Save summary
        summary_file = self.output_dir / f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processing complete! Found {total_beans} coffee bean products across {len(html_files)} files")
        logger.info(f"Results saved to: {self.output_dir}")
        logger.info(f"Summary saved to: {summary_file}")
        
        return summary
        """Test the menu extraction with a sample HTML content"""
        html_path = "/Users/ronballer/Documents/GitHub/BeanO-Project/data_collection/crawling/scraped_data/test_folder/Best coffee to buy online. Coffee Subscriptions. Strong and Freshly Roasted. Locally owned coffee company.html"
        
        logger.info("Testing menu extraction with HTML file...")
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                    sample_html = f.read()
        except Exception as e:
            logger.error(f"Error reading HTML file: {e}")
            return {
                'test_type': 'menu_sample',
                'processed_at': datetime.now().isoformat(),
                'error': str(e)
            }
        # Extract menu items using the new function
        menu_items = self.extract_menu_items_from_html(sample_html)
        
        result = {
            'test_type': 'menu_sample',
            'processed_at': datetime.now().isoformat(),
            'menu_items': menu_items,
            'items_found': len(menu_items)
        }
        
        # Save test result
        test_file = self.output_dir / f"test_menu_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Test complete! Found {len(menu_items)} menu items")
        logger.info(f"Test result saved to: {test_file}")
        
        return result


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Process HTML files from cafe scraper using Gemini to extract coffee bean information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all HTML files in a directory
  python gemini_base_processor.py --directory ./scraped_html_20240101_120000
  
  # Test with sample coffee bean data
  python gemini_base_processor.py --test-sample
  
  # Test menu extraction with sample data
  python gemini_base_processor.py --test-menu
  
  # Set custom API key
  python gemini_base_processor.py --directory ./scraped_html --api-key YOUR_API_KEY
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--directory', '-d',
        type=str,
        help='Directory containing HTML files from cafe scraper'
    )
    group.add_argument(
        '--test-sample', '-t',
        action='store_true',
        help='Test the processor with sample HTML content'
    )
    group.add_argument(
        '--test-menu', '-m',
        action='store_true',
        help='Test the menu extraction with sample HTML content'
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        help='Gemini API key (defaults to GEMINI_API_KEY environment variable)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = GeminiHTMLProcessor(api_key=args.api_key)
        
        if args.test_sample:
            # Test with sample
            result = processor.test_sample()
            print(f"\n{'='*60}")
            print("SAMPLE TEST RESULTS")
            print(f"{'='*60}")
            print(f"Coffee beans found: {result['beans_found']}")
            for i, bean in enumerate(result['coffee_beans'], 1):
                print(f"\n{i}. {bean.get('name', 'Unknown')}")
                print(f"   Weight: {bean.get('weight', 'N/A')}")
                print(f"   Price: {bean.get('price', 'N/A')}")
                print(f"   Producer: {bean.get('producer', 'N/A')}")
                print(f"   Region: {bean.get('region', 'N/A')}")
                print(f"   Roast: {bean.get('roast_level', 'N/A')}")
                print(f"   Flavors: {', '.join(bean.get('flavor_notes', []))}")
                print(f"   Grind: {bean.get('grind_type', 'N/A')}")
        
        elif args.test_menu:
            # Test menu extraction
            result = processor.test_menu_sample()
            print(f"\n{'='*60}")
            print("MENU TEST RESULTS")
            print(f"{'='*60}")
            print(f"Menu items found: {result['items_found']}")
            for i, item in enumerate(result['menu_items'], 1):
                print(f"\n{i}. {item.get('name', 'Unknown')}")
                print(f"   Category: {item.get('category', 'N/A')}")
                print(f"   Price: {item.get('price', 'N/A')}")
                print(f"   Description: {item.get('description', 'N/A')}")
                if item.get('size_options'):
                    print(f"   Sizes: {', '.join(item.get('size_options', []))}")
                if item.get('dietary_notes'):
                    print(f"   Dietary Notes: {', '.join(item.get('dietary_notes', []))}")
        
        else:
            # Process directory
            result = processor.process_directory(args.directory)
            print(f"\n{'='*60}")
            print("PROCESSING RESULTS")
            print(f"{'='*60}")
            print(f"Input directory: {result['input_directory']}")
            print(f"Files processed: {result['files_processed']}")
            print(f"Total coffee beans found: {result['total_beans_found']}")
            print(f"Average beans per file: {result['total_beans_found'] / max(result['files_processed'], 1):.1f}")
            
            # Show files with most beans
            files_with_beans = [r for r in result['results'] if r.get('beans_found', 0) > 0]
            if files_with_beans:
                print(f"\nFiles with coffee bean products:")
                for file_result in sorted(files_with_beans, key=lambda x: x.get('beans_found', 0), reverse=True)[:10]:
                    print(f"  {file_result['source_file']}: {file_result.get('beans_found', 0)} beans")
            
            print(f"\nResults saved to: {processor.output_dir}")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
