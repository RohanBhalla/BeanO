import json
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import re
from bs4 import BeautifulSoup

# Import models
try:
    from .models import CoffeeBean, BeanInfo, SpecialtyBeanInfo, MenuItem, CafeMenu, ScrapedData
except ImportError:
    from models import CoffeeBean, BeanInfo, SpecialtyBeanInfo, MenuItem, CafeMenu, ScrapedData

# For local LLM usage (you can replace with your preferred LLM)
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

logger = logging.getLogger(__name__)

@dataclass
class LLMConfig:
    """Configuration for LLM processing"""
    model_type: str = "openai"  # "openai", "qwen", "local", or "mock"
    model_name: str = "gpt-3.5-turbo"  # or "Qwen/Qwen2-7B-Instruct" for local Qwen
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2000
    chunk_size: int = 4000  # Max chars per chunk to send to LLM
    device: str = "auto"  # "auto", "cpu", "cuda", "mps" for local models
    load_in_8bit: bool = False  # Use 8-bit quantization to save memory
    load_in_4bit: bool = False  # Use 4-bit quantization to save even more memory

class LLMProcessor:
    """Process HTML content using LLM to extract structured coffee information"""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self._setup_model()
    
    def _setup_model(self):
        """Initialize the LLM model based on configuration"""
        if self.config.model_type == "openai" and HAS_OPENAI:
            if self.config.api_key:
                openai.api_key = self.config.api_key
            self.model = "openai"
            self.tokenizer = None
        elif self.config.model_type == "qwen" and HAS_TRANSFORMERS:
            self._setup_qwen_model()
        elif self.config.model_type == "local" and HAS_TRANSFORMERS:
            # Example with a local model - you can replace with your preferred model
            self.model = pipeline("text-generation", model="microsoft/DialoGPT-medium")
            self.tokenizer = None
        else:
            logger.warning("Using mock LLM processor - replace with actual LLM integration")
            self.model = "mock"
            self.tokenizer = None
    
    def _setup_qwen_model(self):
        """Setup Qwen model for local inference"""
        try:
            logger.info(f"Loading Qwen model: {self.config.model_name}")
            
            # Determine device
            if self.config.device == "auto":
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    device = "mps"  # Apple Silicon
                else:
                    device = "cpu"
            else:
                device = self.config.device
            
            logger.info(f"Using device: {device}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                trust_remote_code=True
            )
            
            # Configure model loading options
            model_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if device != "cpu" else torch.float32,
            }
            
            # Add quantization if requested
            if self.config.load_in_4bit:
                from transformers import BitsAndBytesConfig
                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
            elif self.config.load_in_8bit:
                model_kwargs["load_in_8bit"] = True
            else:
                model_kwargs["device_map"] = device
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                **model_kwargs
            )
            
            # Move to device if not using device_map
            if not (self.config.load_in_4bit or self.config.load_in_8bit):
                self.model = self.model.to(device)
            
            self.model.eval()
            logger.info("Qwen model loaded successfully!")
            
        except Exception as e:
            logger.error(f"Failed to load Qwen model: {e}")
            logger.warning("Falling back to mock LLM")
            self.model = "mock"
            self.tokenizer = None
    
    def _generate_qwen_response(self, prompt: str) -> str:
        """Generate response using Qwen model"""
        try:
            # Format prompt for Qwen chat format
            messages = [
                {"role": "system", "content": "You are a helpful JSON‐extraction assistant specialized in coffee‐bean data structured information from coffee shop websites. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ]
            
            # Apply chat template
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Tokenize
            model_inputs = self.tokenizer([text], return_tensors="pt")
            
            # Move to same device as model
            device = next(self.model.parameters()).device
            model_inputs = {k: v.to(device) for k, v in model_inputs.items()}
            
            # Generate
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **model_inputs,
                    max_new_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    do_sample=self.config.temperature > 0,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # Decode only the new tokens
            new_tokens = generated_ids[0][len(model_inputs["input_ids"][0]):]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Qwen generation error: {e}")
            return self._mock_llm_response(prompt)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split large text into manageable chunks"""
        chunks = []
        current_chunk = ""
        
        # Split by sentences to maintain context
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence in sentences:
            if len(current_chunk + sentence) < self.config.chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt"""
        if self.model == "openai" and HAS_OPENAI:
            try:
                response = openai.ChatCompletion.create(
                    model=self.config.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                return self._mock_llm_response(prompt)
        
        elif self.config.model_type == "qwen" and hasattr(self, 'tokenizer') and self.tokenizer is not None:
            return self._generate_qwen_response(prompt)
        
        elif self.model == "mock":
            return self._mock_llm_response(prompt)
        
        else:
            logger.error("No suitable LLM model available")
            return "{}"
    
    def _mock_llm_response(self, prompt: str) -> str:
        """Mock LLM response for testing - replace with actual LLM"""
        if "coffee bean" in prompt.lower() or "roast" in prompt.lower():
            return json.dumps({
                "beans": [{
                    "name": "Example Ethiopian Single Origin",
                    "weight": "12oz",
                    "price": "$18.99",
                    "producer": "Yirgacheffe Cooperative",
                    "region": "Yirgacheffe, Ethiopia",
                    "roast_level": "medium",
                    "flavor_notes": ["citrus", "floral", "bright acidity"],
                    "grind_type": "whole",
                    "farm": "Konga Cooperative",
                    "altitude": "1800-2000 masl",
                    "process": "washed",
                    "bean_type": "arabica",
                    "variety": "Heirloom"
                }]
            })
        elif "menu" in prompt.lower() or "beverage" in prompt.lower():
            return json.dumps({
                "menu_items": [{
                    "name": "Cappuccino",
                    "description": "Espresso with steamed milk and foam",
                    "price": "$4.50",
                    "sizes": ["8oz", "12oz"],
                    "category": "espresso drinks"
                }]
            })
        return "{}"
    
    def extract_coffee_beans(self, html_content: str, url: str) -> List[CoffeeBean]:
        """Extract coffee bean information from HTML content"""
        # Clean HTML and extract text
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text()
        
        # Create prompt for bean extraction
        prompt = f"""
        Extract coffee bean information from the following text content from a coffee shop website.
        
        Return ONLY valid JSON in this exact format:
        {{
            "beans": [
                {{
                    "name": "bean or blend name",
                    "weight": "weight with units such as 12oz, 1lb, 250g, etc.",
                    "price": "price with currency",
                    "producer": "producer/farm name listed with farm or producer name",
                    "region": "growing region listed next to regions tag",
                    "roast_level": "light|medium-light|medium|medium-dark|dark",
                    "flavor_notes": ["flavor notes listed as the taste of the coffee"],
                    "grind_type": "whole|ground",
                    "farm": "farm name if available",
                    "altitude": "altitude in masl if available listed next to altitude tag",
                    "process": "natural|washed|honey|pulped_natural|wet_hulled",
                    "agtron_roast_level": "agtron number if available",
                    "suitable_brew_types": ["espresso", "drip", "pour_over"],
                    "bean_type": "arabica|robusta|liberica|excelsa",
                    "variety": "coffee variety/cultivar if available"
                }}
            ]
        }}
        
        If no coffee beans are found, return: {{"beans": []}}
        
        Website content:
        {text_content[:3000]}...
        """
        
        try:
            response = self._call_llm(prompt)
            data = json.loads(response)
            
            beans = []
            for bean_data in data.get("beans", []):
                # Create basic info
                basic_info = BeanInfo(
                    name=bean_data.get("name"),
                    weight=bean_data.get("weight"),
                    price=bean_data.get("price"),
                    producer=bean_data.get("producer"),
                    region=bean_data.get("region"),
                    roast_level=bean_data.get("roast_level"),
                    flavor_notes=bean_data.get("flavor_notes"),
                    grind_type=bean_data.get("grind_type")
                )
                
                # Create specialty info if available
                specialty_info = None
                if any(bean_data.get(key) for key in ["farm", "altitude", "process", "agtron_roast_level", "suitable_brew_types", "bean_type", "variety"]):
                    specialty_info = SpecialtyBeanInfo(
                        farm=bean_data.get("farm"),
                        altitude=bean_data.get("altitude"),
                        process=bean_data.get("process"),
                        agtron_roast_level=bean_data.get("agtron_roast_level"),
                        suitable_brew_types=bean_data.get("suitable_brew_types"),
                        bean_type=bean_data.get("bean_type"),
                        variety=bean_data.get("variety")
                    )
                
                bean = CoffeeBean(
                    basic_info=basic_info,
                    specialty_info=specialty_info,
                    raw_html=html_content,
                    source_url=url
                )
                beans.append(bean)
            
            return beans
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response for beans: {e}")
            return []
        except Exception as e:
            logger.error(f"Error extracting beans: {e}")
            return []
    
    def extract_menu_items(self, html_content: str, url: str) -> Optional[CafeMenu]:
        """Extract menu items from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text()
        
        # Extract cafe name from title or content
        title = soup.find('title')
        cafe_name = title.get_text().strip() if title else None
        
        prompt = f"""
        Extract coffee menu items from the following text content from a coffee shop website.
        
        Return ONLY valid JSON in this exact format:
        {{
            "menu_items": [
                {{
                    "name": "beverage name",
                    "description": "description if available",
                    "price": "price with currency",
                    "sizes": ["size1", "size2"],
                    "category": "category like espresso, specialty drinks, etc",
                    "ingredients": ["ingredient1", "ingredient2"]
                }}
            ]
        }}
        
        Focus on coffee beverages, not food items. If no menu items are found, return: {{"menu_items": []}}
        
        Website content:
        {text_content[:3000]}...
        """
        
        try:
            response = self._call_llm(prompt)
            data = json.loads(response)
            
            menu_items = []
            for item_data in data.get("menu_items", []):
                item = MenuItem(
                    name=item_data.get("name", ""),
                    description=item_data.get("description"),
                    price=item_data.get("price"),
                    sizes=item_data.get("sizes"),
                    category=item_data.get("category"),
                    ingredients=item_data.get("ingredients")
                )
                menu_items.append(item)
            
            if menu_items:
                return CafeMenu(
                    items=menu_items,
                    cafe_name=cafe_name,
                    source_url=url
                )
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response for menu: {e}")
        except Exception as e:
            logger.error(f"Error extracting menu: {e}")
        
        return None
    
    def process_crawled_data(self, crawl_result: Dict) -> ScrapedData:
        """Process all crawled pages to extract structured data"""
        logger.info("Processing crawled data with LLM...")
        
        all_beans = []
        menu = None
        
        # Keywords to identify relevant pages
        bean_keywords = ["coffee", "bean", "roast", "origin", "single origin", "blend", "espresso"]
        menu_keywords = ["menu", "drinks", "beverages", "cappuccino", "latte", "americano"]
        
        for page in crawl_result['pages']:
            url = page['url']
            html_content = page['html_content']
            text_content = page['clean_text'].lower()
            
            # Check if page likely contains bean information
            if any(keyword in text_content for keyword in bean_keywords):
                logger.info(f"Processing beans from: {url}")
                beans = self.extract_coffee_beans(html_content, url)
                all_beans.extend(beans)
            
            # Check if page likely contains menu information
            if any(keyword in text_content for keyword in menu_keywords) and not menu:
                logger.info(f"Processing menu from: {url}")
                extracted_menu = self.extract_menu_items(html_content, url)
                if extracted_menu and extracted_menu.items:
                    menu = extracted_menu
        
        # Extract cafe name from the main page
        cafe_name = None
        if crawl_result['pages']:
            main_page = crawl_result['pages'][0]  # First page is usually the homepage
            soup = BeautifulSoup(main_page['html_content'], 'html.parser')
            title = soup.find('title')
            if title:
                cafe_name = title.get_text().strip()
        
        return ScrapedData(
            cafe_name=cafe_name,
            base_url=crawl_result['start_url'],
            coffee_beans=all_beans,
            menu=menu,
            all_urls_crawled=crawl_result['visited_urls']
        ) 