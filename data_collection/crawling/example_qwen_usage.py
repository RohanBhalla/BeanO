#!/usr/bin/env python3

# NOTE: This script requires Python 3! Use: python3 example_qwen_usage.py
"""
Example usage of the Cafe Scraper with Qwen Models

This script demonstrates how to use locally-run Qwen models for coffee shop 
website scraping and data extraction.
"""

import os
import logging
import torch

try:
    from cafe_scraper import CafeScraper, LLMConfig
except ImportError:
    from .cafe_scraper import CafeScraper, LLMConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_system_requirements():
    """Check if system supports running Qwen models"""
    print("🔍 Checking System Requirements...")
    
    # Check PyTorch
    print(f"✅ PyTorch version: {torch.__version__}")
    
    # Check CUDA
    if torch.cuda.is_available():
        print(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print(f"✅ Apple Silicon (MPS) available")
    else:
        print(f"⚠️  Using CPU only - this will be slower")
    
    # Check transformers
    try:
        import transformers
        print(f"✅ Transformers version: {transformers.__version__}")
    except ImportError:
        print(f"❌ Transformers not installed")
        return False
    
    return True

def example_qwen_2_0_5b():
    """Example using Qwen2-0.5B (lightweight model)"""
    print("\n=== Qwen2-0.5B Example (Lightweight) ===")
    
    # Configure for small Qwen model
    llm_config = LLMConfig(
        model_type="qwen",
        model_name="Qwen/Qwen2-0.5B-Instruct",
        temperature=0.1,
        max_tokens=1000,
        device="auto",
        load_in_8bit=False,  # Small model doesn't need quantization
        load_in_4bit=False
    )
    
    try:
        scraper = CafeScraper(llm_config)
        
        # Test with Partners Coffee
        result = scraper.scrape_cafe_website(
            url="https://www.partnerscoffee.com/",
            output_file="results/partners_qwen_0_5b.json"
        )
        
        scraper.print_summary(result)
        
        print(f"\n✅ Qwen2-0.5B processing completed!")
        print(f"Found {len(result.coffee_beans)} coffee beans")
        
    except Exception as e:
        print(f"❌ Error with Qwen2-0.5B: {e}")

def example_qwen_2_1_5b():
    """Example using Qwen2-1.5B (balanced model)"""
    print("\n=== Qwen2-1.5B Example (Balanced) ===")
    
    # Configure for medium Qwen model
    llm_config = LLMConfig(
        model_type="qwen",
        model_name="Qwen/Qwen2-1.5B-Instruct",
        temperature=0.1,
        max_tokens=1500,
        device="auto",
        load_in_8bit=True,  # Use 8-bit to save memory
        load_in_4bit=False
    )
    
    try:
        scraper = CafeScraper(llm_config)
        
        result = scraper.scrape_cafe_website(
            url="https://www.partnerscoffee.com/",
            output_file="results/partners_qwen_1_5b.json"
        )
        
        scraper.print_summary(result)
        
        print(f"\n✅ Qwen2-1.5B processing completed!")
        
    except Exception as e:
        print(f"❌ Error with Qwen2-1.5B: {e}")

def example_qwen_2_7b():
    """Example using Qwen2-7B (high-quality model)"""
    print("\n=== Qwen2-7B Example (High Quality) ===")
    
    # Check if we have enough memory for 7B model
    if torch.cuda.is_available():
        memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
        if memory_gb < 12:
            print(f"⚠️  Warning: Only {memory_gb:.1f}GB GPU memory available.")
            print("   Qwen2-7B may require quantization or might not fit.")
    
    # Configure for large Qwen model with quantization
    llm_config = LLMConfig(
        model_type="qwen",
        model_name="Qwen/Qwen2-7B-Instruct",
        temperature=0.1,
        max_tokens=2000,
        device="auto",
        load_in_8bit=False,
        load_in_4bit=True  # Use 4-bit quantization for 7B model
    )
    
    try:
        scraper = CafeScraper(llm_config)
        
        result = scraper.scrape_cafe_website(
            url="https://www.partnerscoffee.com/",
            output_file="results/partners_qwen_7b.json"
        )
        
        scraper.print_summary(result)
        
        print(f"\n✅ Qwen2-7B processing completed!")
        
        # Show detailed results for high-quality model
        if result.coffee_beans:
            print(f"\n=== Detailed Results from Qwen2-7B ===")
            for i, bean in enumerate(result.coffee_beans[:3], 1):
                print(f"\n{i}. {bean.basic_info.name or 'Unnamed Bean'}")
                if bean.basic_info.price:
                    print(f"   💰 Price: {bean.basic_info.price}")
                if bean.basic_info.region:
                    print(f"   🌍 Region: {bean.basic_info.region}")
                if bean.basic_info.roast_level:
                    print(f"   🔥 Roast: {bean.basic_info.roast_level}")
                if bean.basic_info.flavor_notes:
                    print(f"   👅 Flavors: {', '.join(bean.basic_info.flavor_notes)}")
                
                if bean.specialty_info:
                    if bean.specialty_info.farm:
                        print(f"   🏔️  Farm: {bean.specialty_info.farm}")
                    if bean.specialty_info.altitude:
                        print(f"   📏 Altitude: {bean.specialty_info.altitude}")
                    if bean.specialty_info.process:
                        print(f"   ⚙️  Process: {bean.specialty_info.process}")
        
    except Exception as e:
        print(f"❌ Error with Qwen2-7B: {e}")
        print("   Try using a smaller model or enabling quantization")

def example_custom_qwen_config():
    """Example with custom Qwen configuration"""
    print("\n=== Custom Qwen Configuration Example ===")
    
    # Custom configuration optimized for coffee extraction
    llm_config = LLMConfig(
        model_type="qwen",
        model_name="Qwen/Qwen2-1.5B-Instruct",  # Good balance
        temperature=0.05,  # Very low for consistent extraction
        max_tokens=1200,   # Sufficient for coffee data
        device="auto",
        load_in_8bit=True,
        chunk_size=3000    # Smaller chunks for better processing
    )
    
    try:
        scraper = CafeScraper(llm_config)
        
        # Demonstrate with different cafe
        result = scraper.scrape_cafe_website(
            url="https://www.partnerscoffee.com/",
            output_file="results/partners_custom_qwen.json"
        )
        
        summary = scraper.get_summary(result)
        
        print(f"\n📊 Custom Qwen Results:")
        print(f"   Coffee beans found: {summary['coffee_beans']['total_count']}")
        print(f"   Menu items found: {summary['menu']['total_items']}")
        print(f"   Pages crawled: {summary['total_pages_crawled']}")
        
        if summary['coffee_beans']['unique_regions']:
            print(f"   Regions discovered: {', '.join(summary['coffee_beans']['unique_regions'])}")
        
    except Exception as e:
        print(f"❌ Error with custom Qwen config: {e}")

def compare_model_sizes():
    """Compare different Qwen model sizes"""
    print("\n=== Model Size Comparison ===")
    
    models_to_test = [
        ("Qwen/Qwen2-0.5B-Instruct", "0.5B - Fast, lower quality"),
        ("Qwen/Qwen2-1.5B-Instruct", "1.5B - Balanced speed/quality"),
        # ("Qwen/Qwen2-7B-Instruct", "7B - Slow, high quality"),  # Comment out if too big
    ]
    
    results = {}
    
    for model_name, description in models_to_test:
        print(f"\n🧪 Testing {model_name} ({description})")
        
        llm_config = LLMConfig(
            model_type="qwen",
            model_name=model_name,
            temperature=0.1,
            max_tokens=800,
            load_in_8bit=True
        )
        
        try:
            import time
            start_time = time.time()
            
            scraper = CafeScraper(llm_config)
            
            # Quick test on a single page (not full crawl)
            from web_crawler import create_coffee_crawler
            crawler = create_coffee_crawler()
            
            # Just crawl the homepage for quick comparison
            crawl_result = crawler.crawl_website("https://www.partnerscoffee.com/")
            if crawl_result['pages']:
                # Process just the first page
                test_result = scraper.llm_processor.process_crawled_data({
                    'pages': crawl_result['pages'][:1],  # Just first page
                    'start_url': crawl_result['start_url'],
                    'visited_urls': crawl_result['visited_urls'][:1]
                })
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                results[model_name] = {
                    'time': processing_time,
                    'beans': len(test_result.coffee_beans),
                    'menu_items': len(test_result.menu.items) if test_result.menu else 0
                }
                
                print(f"   ⏱️  Processing time: {processing_time:.1f}s")
                print(f"   ☕ Beans found: {results[model_name]['beans']}")
                print(f"   🍵 Menu items: {results[model_name]['menu_items']}")
            
            crawler.close()
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results[model_name] = {'error': str(e)}
    
    # Summary
    print(f"\n📈 Comparison Summary:")
    for model_name, result in results.items():
        if 'error' not in result:
            print(f"   {model_name.split('/')[-1]}: {result['time']:.1f}s, {result['beans']} beans, {result['menu_items']} menu items")

def main():
    """Run Qwen examples"""
    print("🤖 QWEN CAFE SCRAPER EXAMPLES")
    print("=" * 50)
    
    # Check requirements
    if not check_system_requirements():
        print("❌ System requirements not met. Please install missing packages.")
        return
    
    # Create results directory
    os.makedirs("results", exist_ok=True)
    
    # Run examples (comment out any that are too resource-intensive)
    try:
        example_qwen_2_0_5b()      # Start with smallest model
        example_qwen_2_1_5b()      # Balanced model
        # example_qwen_2_7b()        # Uncomment if you have enough memory
        example_custom_qwen_config()
        # compare_model_sizes()      # Uncomment for detailed comparison
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    
    print("\n✅ Qwen examples completed!")
    print("\n💡 Tips for better performance:")
    print("   - Use smaller models (0.5B, 1.5B) for faster processing")
    print("   - Enable quantization (load_in_8bit/load_in_4bit) to save memory")
    print("   - Adjust temperature (0.05-0.2) for more consistent extraction")
    print("   - Use GPU if available for much faster inference")

if __name__ == "__main__":
    main() 