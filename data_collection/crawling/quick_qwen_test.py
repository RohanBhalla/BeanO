#!/usr/bin/env python3

# NOTE: This script requires Python 3! Use: python3 quick_qwen_test.py
"""
Quick Qwen Test Script

Simple script to test Qwen model integration with the cafe scraper.
Uses the smallest Qwen model for fast testing.
"""

import sys
import logging

try:
    from cafe_scraper import CafeScraper, LLMConfig
except ImportError:
    from .cafe_scraper import CafeScraper, LLMConfig

def quick_qwen_test(url=None):
    """Quick test of Qwen integration"""
    print("🤖 Quick Qwen Test")
    print("=" * 30)
    
    # Use provided URL or default
    test_url = url or "https://www.partnerscoffee.com/"
    
    # Configure Qwen with smallest model for fastest test
    llm_config = LLMConfig(
        model_type="qwen",
        model_name="Qwen/Qwen2-0.5B-Instruct",  # Smallest model
        temperature=0.1,
        max_tokens=800,
        device="auto",
        load_in_8bit=False,  # No quantization for small model
        load_in_4bit=False
    )
    
    print(f"🔗 Testing URL: {test_url}")
    print(f"🧠 Model: {llm_config.model_name}")
    print(f"⚙️  Device: {llm_config.device}")
    
    try:
        # Create scraper
        print("\n📥 Loading Qwen model...")
        scraper = CafeScraper(llm_config)
        
        # Run scraper
        print("🕷️  Starting crawl and extraction...")
        result = scraper.scrape_cafe_website(
            url=test_url,
            output_file="results/qwen_quick_test.json"
        )
        
        # Show results
        print("\n🎉 Test completed successfully!")
        print(f"☕ Coffee beans found: {len(result.coffee_beans)}")
        print(f"🍵 Menu items found: {len(result.menu.items) if result.menu else 0}")
        print(f"📄 Pages crawled: {len(result.all_urls_crawled)}")
        
        # Show sample bean if found
        if result.coffee_beans:
            bean = result.coffee_beans[0]
            print(f"\n📋 Sample Bean:")
            print(f"   Name: {bean.basic_info.name or 'N/A'}")
            print(f"   Price: {bean.basic_info.price or 'N/A'}")
            print(f"   Region: {bean.basic_info.region or 'N/A'}")
            print(f"   Roast: {bean.basic_info.roast_level or 'N/A'}")
        
        # Show sample menu item if found
        if result.menu and result.menu.items:
            item = result.menu.items[0]
            print(f"\n🍺 Sample Menu Item:")
            print(f"   Name: {item.name}")
            print(f"   Price: {item.price or 'N/A'}")
            print(f"   Description: {item.description or 'N/A'}")
        
        print(f"\n💾 Results saved to: results/qwen_quick_test.json")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Make sure you have all dependencies: pip install -r requirements.txt")
        print("   2. Check if you have enough memory for the model")
        print("   3. Try with mock mode first: change model_type to 'mock'")
        print("   4. Check internet connection for model download")
        return False

def main():
    """Main function"""
    # Set up basic logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise for quick test
    
    # Get URL from command line if provided
    url = sys.argv[1] if len(sys.argv) > 1 else None
    
    if url:
        print(f"Using provided URL: {url}")
    else:
        print("Using default URL: https://www.partnerscoffee.com/")
        print("(You can provide a different URL as argument)")
    
    # Run test
    success = quick_qwen_test(url)
    
    if success:
        print("\n✅ Qwen integration is working!")
        print("\n🚀 Next steps:")
        print("   - Try different Qwen models: Qwen2-1.5B-Instruct, Qwen2-7B-Instruct")
        print("   - Run full examples: python example_qwen_usage.py")
        print("   - Test on different cafe websites")
    else:
        print("\n💡 For more detailed testing, try: python example_qwen_usage.py")

if __name__ == "__main__":
    main() 