from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import re
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

def extract_username_from_url(url):
    """Extract username from Vinted profile URL"""
    patterns = [
        r'vinted\.[a-z]+/member/(\d+)-([^/\?]+)',
        r'vinted\.[a-z]+/user/([^/\?]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            if len(match.groups()) > 1:
                return match.group(2)
            return match.group(1)
    return None

def get_vinted_user_data(username):
    """Get user data from Vinted using their API"""
    try:
        # Try different Vinted domains
        domains = ['vinted.co.uk', 'vinted.com', 'vinted.fr']
        
        for domain in domains:
            url = f"https://www.{domain}/api/v2/users/{username}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                user_data = data.get('user', {})
                
                return {
                    'success': True,
                    'user': {
                        'id': user_data.get('id'),
                        'login': user_data.get('login', username),
                        'real_name': user_data.get('real_name', ''),
                        'given_item_count': user_data.get('given_item_count', 0),
                        'taken_item_count': user_data.get('taken_item_count', 0),
                        'followers_count': user_data.get('followers_count', 0),
                        'following_count': user_data.get('following_count', 0),
                        'positive_feedback_count': user_data.get('positive_feedback_count', 0),
                        'negative_feedback_count': user_data.get('negative_feedback_count', 0),
                        'feedback_reputation': user_data.get('feedback_reputation', 0),
                        'avatar_url': user_data.get('photo', {}).get('url') if user_data.get('photo') else None,
                        'city': user_data.get('city', ''),
                        'country': user_data.get('country_title', ''),
                        'verification': {
                            'email': user_data.get('verification', {}).get('email', False),
                            'facebook': user_data.get('verification', {}).get('facebook', False),
                            'google': user_data.get('verification', {}).get('google', False),
                            'phone': user_data.get('verification', {}).get('phone', False),
                        }
                    }
                }
        
        return {'success': False, 'error': 'User not found'}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_user_items(user_id, page=1):
    """Get items from a user's closet"""
    try:
        domains = ['vinted.co.uk', 'vinted.com', 'vinted.fr']
        
        for domain in domains:
            url = f"https://www.{domain}/api/v2/users/{user_id}/items"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            params = {
                'page': page,
                'per_page': 20,
                'order': 'relevance'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                products = []
                for item in items:
                    products.append({
                        'id': str(item.get('id')),
                        'title': item.get('title', ''),
                        'description': item.get('description', ''),
                        'price': float(item.get('price', 0)),
                        'currency': item.get('currency', 'EUR'),
                        'size': item.get('size_title', ''),
                        'brand': item.get('brand_title', ''),
                        'condition': item.get('status', ''),
                        'category': item.get('catalog_title', ''),
                        'color': '',  # Not directly available
                        'material': '',  # Not directly available
                        'imageUrls': [photo.get('url') for photo in item.get('photos', []) if photo.get('url')],
                        'url': f"https://www.{domain}/items/{item.get('id')}",
                        'isSelected': True
                    })
                
                return {
                    'success': True,
                    'products': products,
                    'pagination': data.get('pagination', {})
                }
        
        return {'success': False, 'error': 'Could not fetch items'}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Vinted Scraper API (Simple Version)',
        'endpoints': {
            '/health': 'Health check',
            '/user/<username>': 'Get user profile info',
            '/user/<username>/items': 'Get user items',
            '/scrape/<username>': 'Get user profile and all items'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Vinted Scraper API is running'})

@app.route('/user/<username>', methods=['GET'])
def get_user(username):
    """Get user profile information"""
    result = get_vinted_user_data(username)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 404

@app.route('/user/<username>/items', methods=['GET'])
def get_user_items_endpoint(username):
    """Get items from a user's closet"""
    page = request.args.get('page', 1, type=int)
    
    # First get user ID
    user_result = get_vinted_user_data(username)
    if not user_result['success']:
        return jsonify(user_result), 404
    
    user_id = user_result['user']['id']
    
    # Get items
    items_result = get_user_items(user_id, page)
    
    if items_result['success']:
        return jsonify(items_result)
    else:
        return jsonify(items_result), 500

@app.route('/scrape/<username>', methods=['GET'])
def scrape_user(username):
    """Get complete user data including all items"""
    # Get user info
    user_result = get_vinted_user_data(username)
    if not user_result['success']:
        return jsonify(user_result), 404
    
    user_id = user_result['user']['id']
    all_products = []
    page = 1
    
    # Fetch all pages of items
    while True:
        items_result = get_user_items(user_id, page)
        if not items_result['success']:
            break
        
        all_products.extend(items_result['products'])
        
        # Check if there are more pages
        pagination = items_result.get('pagination', {})
        if page >= pagination.get('total_pages', 1):
            break
        
        page += 1
        
        # Limit to prevent too many requests
        if page > 10:  # Max 200 items (20 per page * 10 pages)
            break
    
    return jsonify({
        'success': True,
        'user': user_result['user'],
        'products': all_products,
        'count': len(all_products)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)