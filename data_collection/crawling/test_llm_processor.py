#!/usr/bin/env python3

# NOTE: This script requires Python 3! Use: python3 test_llm_processor.py

"""
Test LLM Processor with JSON Test Data

This script allows you to test and refine the Qwen LLM processor using 
pre-scraped HTML content stored in a JSON file. Perfect for iterating 
on prompts and extraction logic without re-crawling websites.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from llm_processor import LLMProcessor, LLMConfig
    from models import ScrapedData, CoffeeBean, CafeMenu
except ImportError:
    from .llm_processor import LLMProcessor, LLMConfig
    from .models import ScrapedData, CoffeeBean, CafeMenu

def load_test_data(json_file_path):
    """Load test data from JSON file"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Loaded test data from: {json_file_path}")
        return data
    
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in file: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None

def extract_html_content(test_data):
    """Extract HTML content from test data structure"""
    html_content = None
    
    # Try different possible structures
    if isinstance(test_data, dict):
        # Look for raw_html key directly
        if 'raw_html' in test_data:
            html_content = test_data['raw_html']
            print(f"📄 Found HTML content in 'raw_html' key")
        
        # Look for HTML in coffee beans
        elif 'coffee_beans' in test_data and test_data['coffee_beans']:
            for bean in test_data['coffee_beans']:
                if isinstance(bean, dict) and 'raw_html' in bean:
                    html_content = bean['raw_html']
                    print(f"📄 Found HTML content in coffee bean")
                    break
        
        # Look for HTML in pages array
        elif 'pages' in test_data and test_data['pages']:
            for page in test_data['pages']:
                if isinstance(page, dict) and 'html_content' in page:
                    html_content = page['html_content']
                    print(f"📄 Found HTML content in pages array")
                    break
        
        # Look for any field containing HTML-like content
        else:
            for key, value in test_data.items():
                if isinstance(value, str) and '<html' in value.lower():
                    html_content = value
                    print(f"📄 Found HTML content in '{key}' key")
                    break
    
    if html_content:
        print(f"📏 HTML content length: {len(html_content)} characters")
        # Show preview of HTML
        preview = html_content[:200].replace('\n', ' ')
        print(f"📋 Preview: {preview}...")
        return html_content
    else:
        print(f"❌ No HTML content found in test data")
        print(f"💡 Expected structure: {{'raw_html': '...'}} or {{'pages': [{{'html_content': '...'}}]}}")
        return None

def test_bean_extraction(llm_processor, html_content, url="test-file"):
    """Test coffee bean extraction"""
    print(f"\n🔍 Testing Coffee Bean Extraction")
    print("=" * 40)
    
    try:
        beans = llm_processor.extract_coffee_beans(html_content, url)
        
        print(f"☕ Found {len(beans)} coffee beans")
        
        for i, bean in enumerate(beans, 1):
            print(f"\n{i}. Bean: {bean.basic_info.name or 'Unnamed'}")
            print(f"   💰 Price: {bean.basic_info.price or 'N/A'}")
            print(f"   🌍 Region: {bean.basic_info.region or 'N/A'}")
            print(f"   🔥 Roast: {bean.basic_info.roast_level or 'N/A'}")
            
            if bean.basic_info.flavor_notes:
                print(f"   👅 Flavors: {', '.join(bean.basic_info.flavor_notes)}")
            
            if bean.specialty_info:
                if bean.specialty_info.farm:
                    print(f"   🏔️  Farm: {bean.specialty_info.farm}")
                if bean.specialty_info.process:
                    print(f"   ⚙️  Process: {bean.specialty_info.process}")
                if bean.specialty_info.altitude:
                    print(f"   📏 Altitude: {bean.specialty_info.altitude}")
        
        return beans
        
    except Exception as e:
        print(f"❌ Bean extraction failed: {e}")
        return []

def test_menu_extraction(llm_processor, html_content, url="test-file"):
    """Test menu extraction"""
    print(f"\n🍵 Testing Menu Extraction")
    print("=" * 35)
    
    try:
        menu = llm_processor.extract_menu_items(html_content, url)
        
        if menu and menu.items:
            print(f"🍺 Found {len(menu.items)} menu items")
            
            for i, item in enumerate(menu.items, 1):
                print(f"\n{i}. {item.name}")
                if item.price:
                    print(f"   💰 Price: {item.price}")
                if item.description:
                    print(f"   📝 Description: {item.description}")
                if item.sizes:
                    print(f"   📏 Sizes: {', '.join(item.sizes)}")
                if item.category:
                    print(f"   📂 Category: {item.category}")
        else:
            print(f"❌ No menu items found")
            
        return menu
        
    except Exception as e:
        print(f"❌ Menu extraction failed: {e}")
        return None

def interactive_refinement(llm_processor, html_content, url="test-file"):
    """Interactive mode for refining extraction"""
    print(f"\n🔄 Interactive Refinement Mode")
    print("=" * 40)
    print("Commands:")
    print("  'beans' - Extract coffee beans")
    print("  'menu' - Extract menu items")
    print("  'config' - Show current configuration")
    print("  'temp X' - Set temperature to X (e.g., 'temp 0.05')")
    print("  'tokens X' - Set max tokens to X (e.g., 'tokens 1500')")
    print("  'quit' - Exit interactive mode")
    
    while True:
        try:
            command = input(f"\n🤖 Enter command: ").strip().lower()
            
            if command == 'quit' or command == 'exit':
                break
            elif command == 'beans':
                test_bean_extraction(llm_processor, html_content, url)
            elif command == 'menu':
                test_menu_extraction(llm_processor, html_content, url)
            elif command == 'config':
                print(f"Current config:")
                print(f"  Model: {llm_processor.config.model_name}")
                print(f"  Temperature: {llm_processor.config.temperature}")
                print(f"  Max tokens: {llm_processor.config.max_tokens}")
            elif command.startswith('temp '):
                try:
                    temp = float(command.split()[1])
                    llm_processor.config.temperature = temp
                    print(f"✅ Temperature set to {temp}")
                except ValueError:
                    print(f"❌ Invalid temperature value")
            elif command.startswith('tokens '):
                try:
                    tokens = int(command.split()[1])
                    llm_processor.config.max_tokens = tokens
                    print(f"✅ Max tokens set to {tokens}")
                except ValueError:
                    print(f"❌ Invalid token value")
            else:
                print(f"❌ Unknown command: {command}")
                
        except KeyboardInterrupt:
            print(f"\n👋 Exiting interactive mode")
            break

def main():
    """Main function"""
    print("🧪 LLM PROCESSOR TESTING TOOL")
    print("=" * 50)
    
    # Get JSON file path
    json_file = "/Users/ronballer/Documents/GitHub/BeanO/data_collection/crawling/results/test_bean.json"
    if not json_file:
        print("❌ No file specified")
        return
    
    # Load test data
    test_data = load_test_data(json_file)
    if not test_data:
        return
    
    # Extract HTML content
    html_content = extract_html_content(test_data)
    if not html_content:
        return
    
    # Get test URL if available
    test_url = "test-file"
    if isinstance(test_data, dict):
        test_url = test_data.get('base_url', test_data.get('source_url', 'test-file'))
    
    print(f"🔗 Test URL: {test_url}")
    
    # Choose what to do
    print(f"\n🎯 What would you like to test?")
    print("1. Quick test with default Qwen config")
    print("2. Interactive refinement mode")
    print("3. Mock mode (for testing without Qwen)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == '1':
        print(f"\n🚀 Quick Test with Qwen")
        print("=" * 30)
        
        # Default config optimized for coffee extraction
        llm_config = LLMConfig(
            model_type="qwen",
            model_name="Qwen/Qwen2-1.5B-Instruct",
            temperature=0.05,  # Low for consistent extraction
            max_tokens=1500,
            load_in_8bit=True
        )
        
        processor = LLMProcessor(llm_config)
        beans = test_bean_extraction(processor, html_content, test_url)
        menu = test_menu_extraction(processor, html_content, test_url)
        
        # Save results
        if beans or menu:
            output_file = f"test_results_{Path(json_file).stem}.json"
            result_data = ScrapedData(
                base_url=test_url,
                coffee_beans=beans,
                menu=menu,
                timestamp=datetime.now().isoformat()
            )
            
            with open(output_file, 'w') as f:
                json.dump(result_data.dict(), f, indent=2, default=str)
            print(f"\n💾 Results saved to: {output_file}")
    
    elif choice == '2':
        # Interactive mode - use fast model for testing
        llm_config = LLMConfig(
            model_type="qwen",
            model_name="Qwen/Qwen2-0.5B-Instruct",  # Fast for testing
            temperature=0.1,
            max_tokens=1000
        )
        processor = LLMProcessor(llm_config)
        interactive_refinement(processor, html_content, test_url)
    
    elif choice == '3':
        # Mock mode for testing structure
        llm_config = LLMConfig(model_type="mock")
        processor = LLMProcessor(llm_config)
        beans = test_bean_extraction(processor, html_content, test_url)
        menu = test_menu_extraction(processor, html_content, test_url)
    
    print(f"\n✅ Testing completed!")

if __name__ == "__main__":
    main() 