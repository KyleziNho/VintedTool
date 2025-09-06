from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import os
import json
import tempfile
import shutil
import re
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

def extract_username_from_url(url):
    """Extract username from Vinted profile URL"""
    # Pattern for Vinted profile URLs
    patterns = [
        r'vinted\.[a-z]+/member/(\d+)-([^/\?]+)',  # e.g., vinted.co.uk/member/12345-username
        r'vinted\.[a-z]+/user/([^/\?]+)',  # e.g., vinted.com/user/username
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            # Return the username part (not the ID)
            if len(match.groups()) > 1:
                return match.group(2)
            return match.group(1)
    return None

def parse_scraped_data(download_dir):
    """Parse the downloaded data from the scraper output"""
    products = []
    
    # List all subdirectories (each is a product)
    for item_dir in os.listdir(download_dir):
        item_path = os.path.join(download_dir, item_dir)
        if os.path.isdir(item_path):
            product = {
                'id': item_dir,
                'title': item_dir,
                'images': [],
                'description': '',
                'price': 0.0,
                'size': '',
                'brand': '',
                'condition': '',
                'category': '',
                'isSelected': True
            }
            
            # Read description.txt if exists
            desc_file = os.path.join(item_path, 'description.txt')
            if os.path.exists(desc_file):
                with open(desc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    product['description'] = content
                    
                    # Try to extract details from description
                    lines = content.split('\n')
                    for line in lines:
                        line_lower = line.lower()
                        if 'price:' in line_lower or '£' in line or '€' in line:
                            # Extract price
                            price_match = re.search(r'[\d,]+\.?\d*', line)
                            if price_match:
                                try:
                                    product['price'] = float(price_match.group().replace(',', ''))
                                except:
                                    pass
                        elif 'size:' in line_lower:
                            product['size'] = line.split(':', 1)[1].strip()
                        elif 'brand:' in line_lower:
                            product['brand'] = line.split(':', 1)[1].strip()
                        elif 'condition:' in line_lower:
                            product['condition'] = line.split(':', 1)[1].strip()
                        elif 'category:' in line_lower:
                            product['category'] = line.split(':', 1)[1].strip()
            
            # List all images
            for file in os.listdir(item_path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    # Store relative path
                    product['images'].append(f"{item_dir}/{file}")
            
            products.append(product)
    
    return products

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Vinted Scraper API',
        'endpoints': {
            '/health': 'Health check',
            '/scrape/profile/<profile_url>': 'Scrape all items from a Vinted profile',
            '/scrape/item/<item_url>': 'Scrape a single Vinted item'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Vinted Scraper API is running'})

@app.route('/scrape/profile', methods=['POST'])
def scrape_vinted_profile():
    """Scrape all items from a Vinted user profile"""
    try:
        data = request.json
        profile_url = data.get('url')
        
        if not profile_url:
            return jsonify({'success': False, 'error': 'Profile URL is required'}), 400
        
        # Extract username from URL
        username = extract_username_from_url(profile_url)
        if not username:
            username = 'unknown_user'
        
        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp()
        download_dir = os.path.join(temp_dir, 'downloads')
        os.makedirs(download_dir)
        
        try:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            # Activate virtual environment and run scraper
            venv_python = os.path.join(original_cwd, 'venv', 'bin', 'python')
            scraper_path = os.path.join(original_cwd, 'vinted_scraper.py')
            
            cmd = [venv_python, scraper_path, f'--all={profile_url}']
            
            # Run the scraper
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5 minute timeout
                cwd=temp_dir
            )
            
            os.chdir(original_cwd)
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise Exception(f"Scraper failed: {error_msg}")
            
            # Parse the downloaded data
            products = parse_scraped_data(download_dir)
            
            return jsonify({
                'success': True,
                'username': username,
                'products': products,
                'count': len(products)
            })
            
        finally:
            # Clean up
            os.chdir(original_cwd)
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Scraping timeout - profile may have too many items'
        }), 408
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/scrape/item', methods=['POST'])
def scrape_vinted_item():
    """Scrape a single Vinted item"""
    try:
        data = request.json
        item_url = data.get('url')
        
        if not item_url:
            return jsonify({'success': False, 'error': 'Item URL is required'}), 400
        
        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp()
        download_dir = os.path.join(temp_dir, 'downloads')
        os.makedirs(download_dir)
        
        try:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            # Activate virtual environment and run scraper
            venv_python = os.path.join(original_cwd, 'venv', 'bin', 'python')
            scraper_path = os.path.join(original_cwd, 'vinted_scraper.py')
            
            cmd = [venv_python, scraper_path, f'--item={item_url}']
            
            # Run the scraper
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60,  # 1 minute timeout for single item
                cwd=temp_dir
            )
            
            os.chdir(original_cwd)
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise Exception(f"Scraper failed: {error_msg}")
            
            # Parse the downloaded data
            products = parse_scraped_data(download_dir)
            
            if products:
                return jsonify({
                    'success': True,
                    'product': products[0]
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No product data found'
                }), 404
            
        finally:
            # Clean up
            os.chdir(original_cwd)
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Scraping timeout'
        }), 408
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)