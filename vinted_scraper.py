#!/usr/bin/env python3
import os
import argparse
import requests
import re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from urllib.parse import urlparse, urljoin

def sanitize_filename(name):
    """Remove invalid characters from folder name"""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()
def is_valid_vinted_url(url):
    """Check if URL is a valid Vinted item or user URL"""
    parsed = urlparse(url)
    if not parsed.scheme in ('http', 'https'):
        return False
    
    # Check domain
    if 'vinted.' not in parsed.netloc:
        return False
    
    # Check path patterns
    path = parsed.path.lower()
    return any(
        path.startswith(p) 
        for p in ('/items/', '/member/', '/catalog/', '/user/')
    )

def validate_url(url):
    """Ensure URL is properly formatted"""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url if is_valid_vinted_url(url) else None

def extract_article_name(driver):
    """Extract article name from page title in HTML with fallback to unique URL-based name"""
    try:
        # First try to get title from HTML
        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "h1.web_ui__Text__text.web_ui__Text__title.web_ui__Text__left")
            )
        )
        title = title_element.text.strip()
        print(f"✅ Extracted title: {title}")
        return title
    except:
        print(f"❌ Could not extract title from HTML, falling back to URL method")
        
        # Fallback to URL method with item ID to ensure uniqueness
        current_url = driver.current_url
        parsed = urlparse(current_url)
        path = parsed.path
        
        # Extract both the numeric ID and name part from URL
        parts = path.split('/')
        if len(parts) >= 3 and parts[-2] == 'items':
            item_id = parts[-1].split('-')[0]  # Get the numeric ID
            name_part = '-'.join(parts[-1].split('-')[1:])  # Get the rest after ID
            clean_name = f"{item_id}_{name_part}" if name_part else item_id
            return clean_name.replace('-', ' ').title()
        
        # If URL parsing fails too, return a unique timestamp-based name
        return f"item_{int(time.time())}"
    
def get_profile_info(driver):
    """Extract username and profile picture URL"""
    try:
        # Get username
        username_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='profile-username']"))
        )
        username = sanitize_filename(username_element.text.strip())
        
        # Get profile picture URL
        profile_pic_element = driver.find_element(By.CSS_SELECTOR, "div.web_ui__Image__circle img.web_ui__Image__content")
        profile_pic_url = profile_pic_element.get_attribute('src')
        
        return username, profile_pic_url
    except :
        print(f"❌ Could not extract profile info")
        return None, None

def download_profile_pic(username, profile_pic_url, base_folder=""):
    """Download profile picture to username folder"""
    if not username or not profile_pic_url:
        return
        
    try:
        profile_folder = os.path.join(base_folder, username)
        os.makedirs(profile_folder, exist_ok=True)
        
        response = requests.get(profile_pic_url, stream=True, timeout=15)
        response.raise_for_status()
        
        # Determine file extension
        content_type = response.headers.get('content-type', '').lower()
        if 'jpeg' in content_type or 'jpg' in content_type:
            ext = '.jpg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            ext = '.jpg'
        
        filename = os.path.join(profile_folder, f"profilepic{ext}")
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
                
        print(f"✅ Saved profile picture to: {filename}")
        return profile_folder
        
    except :
        print(f"❌ Failed to download profile picture")
        return None
def setup_driver():
    """General setup: looks for chromedriver inside 'drivers/' folder"""
    driver_path = None
    drivers_dir = Path("drivers")
    for root, _, files in os.walk(drivers_dir):
        if "chromedriver" in files:
            driver_path = Path(root) / "chromedriver"
            break

    if not driver_path or not driver_path.exists():
        raise FileNotFoundError("❌ chromedriver not found in 'drivers/' folder")

    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--headless")  # Rimuovi se vuoi vedere il browser

    service = Service(executable_path=str(driver_path))
    return webdriver.Chrome(service=service, options=chrome_options)
def save_description(folder_path, description, price, size, condition, color):
    """Save item description to file using the full path"""
    description_path = os.path.join(folder_path, "description.txt")
    with open(description_path, "w", encoding="utf-8") as f:
        f.write(f"Description: {description}\n")
        f.write(f"Price: {price}\n")
        f.write(f"Size: {size}\n")
        f.write(f"Condition: {condition}\n")
        f.write(f"Color: {color}\n")

def wait_for_carousel_items(driver, min_items=30, timeout=15):
    print("💤 Waiting for carousel items to fully load...")
    return WebDriverWait(driver, timeout).until(
        lambda d: len(d.find_elements(
            By.CSS_SELECTOR, 
            "section.web_ui__Carousel__carousel ul.web_ui__Carousel__content-container li.web_ui__Carousel__content"
        )) >= min_items
    )

def scroll_until_all_items_loaded(driver, expected_count, pause_time=2, max_scrolls=30):
    scrolls = 0
    seen_links = set()

    while scrolls < max_scrolls:
        # Incremental scroll to trigger lazy loading
        scroll_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(0, scroll_height, 300):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.2)

        time.sleep(pause_time)  # wait for items to load after full scroll

        # Get new item links
        current_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/items/']")
        new_links = set(link.get_attribute('href') for link in current_links if link.get_attribute('href'))
        seen_links.update(new_links)

        #print(f"⚠️ Scroll {scrolls+1}: Found {len(seen_links)} unique item URLs")

        # Exit early if all items found
        if expected_count and len(seen_links) >= expected_count:
            print("✅ Loaded all expected items.")
            break

        scrolls += 1

    return list(seen_links)

def get_all_item_urls(user_url):
    driver = setup_driver()
    

    # Wait for the <h2> element to appear that contains the number of items
    try:
        driver.get(user_url)
        time.sleep(2)
        # Get profile info first
        username, profile_pic_url = get_profile_info(driver)

        closet_header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h2.web_ui__Text__text.web_ui__Text__title.web_ui__Text__left"))
        )
        closet_text = closet_header.text.strip()
        #print(f"⚠️ Closet header text: {closet_text}")

        # Extract number using regex
        match = re.search(r"(\d+)", closet_text)
        total_items = int(match.group(1)) if match else 0
        print(f"👔 Total number of items in closet: {total_items}")
    except :
        print(f"❌ Failed to get number of closet items")
        total_items = None

    #print("🔄 Scrolling to load all items...")
    item_urls = scroll_until_all_items_loaded(driver, expected_count=total_items)

    return username, profile_pic_url, item_urls

def download_images(item_url, is_bulk=False, base_folder=""):
    driver = setup_driver()
    try:
        print(f"\n♻️ Starting download for: {item_url}")
        driver.get(item_url)
        time.sleep(3)

        
        
        article_name = extract_article_name(driver)
        folder_name = sanitize_filename(article_name)
        full_folder_path = os.path.join(base_folder, folder_name) if base_folder else folder_name
        os.makedirs(full_folder_path, exist_ok=True)
        
        description_path = os.path.join(full_folder_path, "description.txt")  # Use full path
        if not os.path.exists(description_path):
            # Get article description from meta tag
            description = None
            try:
                meta_desc = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@itemprop='description']//span/span"))
                )
                description = meta_desc.text.strip()
                print(f"✅ Found description: {description[:50]}...")
            except:
                print(f"❌ Could not extract description")
            
            # Get price
            price = None
            try:
                price_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@data-testid='item-price']//p[contains(@class, 'web_ui__Text__text')]"))
                )
                price = price_element.text.strip()
                print(f"✅ Found price: {price}")
            except:
                print("❌ Could not extract price")

            # Get size
            size = None
            try:
                size_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@itemprop='size']/span"))
                )
                size = size_element.text.strip()
                print(f"✅ Found size: {size}")
            except:
                print("❌ Could not extract size")

            # Extract condition (itemProp='status')
            condition = None
            try:
                condition_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@itemprop='status']/span"))
                )
                condition = condition_element.text.strip()
                print(f"✅ Found condition: {condition}")
            except :
                print(f"❌ Could not extract condition")

            # Extract color (itemProp='color')
            color = None
            try:
                color_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@itemprop='color']/span"))
                )
                color = color_element.text.strip()
                print(f"✅ Found color: {color}")
            except :
                print(f"❌ Could not extract color")

            if description or price or size or condition or color:
                save_description(full_folder_path, description, price, size, condition, color)  # Pass full path
                print("✅ Saved item infos to description.txt")
            else:
                print("⚠️ Skipping saving description.txt because one or more info were not found.")
        else:
            print("✅ description.txt already exists, skipping save.")
        
        try:
            print("♻️ Starting image extraction...")
            unique_image_urls = set()

            # Unified image detection approach
            image_selectors = [
                # Primary selectors that exclude profile pics
                "figure.item-description img.web_ui__Image__content",
                "figure.item-photo img.web_ui__Image__content",
                "li.web_ui__Carousel__content img.web_ui__Image__content",
                # Generic selector with additional filtering
                "img.web_ui__Image__content:not([role='img'])"
            ]

            for selector in image_selectors:
                try:
                    images = driver.find_elements(By.CSS_SELECTOR, selector)
                    #print(f"⚠️ Trying selector: '{selector}' - Found {len(images)} images")
                    
                    for img in images:
                        try:
                            img_url = img.get_attribute('src')
                            if img_url and 'vinted.net' in img_url and '/t/' in img_url:
                                if not img_url.startswith('http'):
                                    img_url = urljoin(item_url, img_url)
                                unique_image_urls.add(img_url)
                        except:
                            print(f"❌ Image extraction error")
                    
                    if unique_image_urls:
                        #print(f"✅ Found {len(unique_image_urls)} images using selector: {selector}")
                        break
                        
                except :
                    print(f"❌ Selector failed: {selector}")

            # Final fallback - scroll and retry if no images found
            if not unique_image_urls:
                print("⚠️ No images found with static selectors, trying scroll...")
                for _ in range(3):  # Try 3 scroll attempts
                    driver.execute_script("window.scrollBy(0, 500)")
                    time.sleep(1)
                    images = driver.find_elements(By.CSS_SELECTOR, "img.web_ui__Image__content")
                    for img in images:
                        try:
                            img_url = img.get_attribute('src')
                            if img_url and 'vinted.net' in img_url:
                                unique_image_urls.add(img_url)
                        except:
                            pass
                    if unique_image_urls:
                        break

            #print(f"\n✅ Unique image URLs collected: {len(unique_image_urls)}")

                        # Download each image
            for idx, img_url in enumerate(unique_image_urls, start=1):
                try:
                    print(f"\n♻️ Downloading image {idx}/{len(unique_image_urls)}")
                    #print(f"⚠️ Image URL: {img_url}")

                    response = requests.get(img_url, stream=True, timeout=15)
                    response.raise_for_status()

                    content_type = response.headers.get('content-type', '').lower()
                    #print(f"⚠️ Content-Type: {content_type}")

                    if 'jpeg' in content_type:
                        ext = '.jpg'
                    elif 'png' in content_type:
                        ext = '.png'
                    else:
                        ext = '.jpg' if '.jpeg' in img_url.lower() else '.png'
                        ##print(f" ❌ Unexpected content-type, guessing extension: {ext}")

                    filename = f"{full_folder_path}/{article_name.replace(' ', '_')}_{idx}{ext}"
                    os.makedirs(full_folder_path, exist_ok=True)

                    with open(filename, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)

                    print(f"✅ Saved image to: {filename}")

                except:
                    print(f" ❌ Failed to download image {idx}")
                    with open("failed_images.txt", "a") as fail_log:
                        fail_log.write(f"{img_url}\n")

        except:
            print(f"\n❌Image scraping failed")

    finally:
        driver.quit()
        print(f"\n 👔 {article_name}, informations and images downloaded successfully! 🎉\n")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download images from Vinted listings')
    parser.add_argument('--item', help='Vinted item URL (single item)')
    parser.add_argument('--all', help='Vinted user URL to download all items')
    args = parser.parse_args()

    def check_url_accessible(url):
        """Check if URL exists and is accessible"""
        try:
            driver = setup_driver()
            driver.get(url)
            time.sleep(2)  # Wait for page to load
            
            # Check for 404 page
            if "404" in driver.title.lower() or "not found" in driver.title.lower():
                return False
                
            # Check for Vinted's error message
            error_elements = driver.find_elements(By.CSS_SELECTOR, ".web_ui__Alert__content")
            if error_elements and "not exist" in error_elements[0].text.lower():
                return False
                
            return True
        except Exception as e:
            print(f"❌ Error checking URL: {str(e)}")
            return False
        finally:
            driver.quit()

    try:
        if args.all:
            validated_url = validate_url(args.all)
            if not validated_url:
                print("❌ Invalid Vinted user URL. Expected format: https://www.vinted.com/member/username")
                exit(1)
                
            if not check_url_accessible(validated_url):
                print("❌ User profile not found or inaccessible")
                exit(1)
                
            print(f"♻️ Loading all infos... i promise it will be worth it! 💤\n")
            driver = setup_driver()
            driver.get(validated_url)
            time.sleep(2)
            username, profile_pic_url = get_profile_info(driver)
            
            if not username:
                print("❌ Could not find user profile information")
                exit(1)
                
            print(f"💤 Fetching all item URLs from user: {username}")
            username, profile_pic_url, item_urls = get_all_item_urls(validated_url)
            
            if username and profile_pic_url:
                profile_folder = download_profile_pic(username, profile_pic_url)
                base_folder = username
            else:
                base_folder = ""
                
            total_items = len(item_urls)
            print(f"♻️ Starting download of {total_items} items...\nGrab a coffee and chill ☕️ 🥱, this may take a while... 💤\n")
                
            for index, url in enumerate(item_urls, start=1):
                print(f"\n♻️ Downloading {index} of {total_items} articles:")
                download_images(url, is_bulk=True, base_folder=base_folder)

            print(f"\nThanks for using Vinted Scraper! 🎉\n")
            
        elif args.item:
            validated_url = validate_url(args.item)
            if not validated_url:
                print("❌ Invalid Vinted item URL. Expected format: https://www.vinted.com/items/item-id")
                exit(1)
                
            if not check_url_accessible(validated_url):
                print("❌ Item not found (404 error) or inaccessible")
                exit(1)
                
            download_images(validated_url, is_bulk=False)
            
        else:
            print("⚠️ Please specify --item <URL> or --all <USER URL>")
            print("\nUsage examples:")
            print("  Single item: python vinted_scraper.py --item=\"https://www.vinted.com/items/1234567890-dress\"")
            print("  User profile: python vinted_scraper.py --all=\"https://www.vinted.com/member/username\"")
            
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Critical error: {str(e)}")
