# 🛍️ Vinted Scraper Downloader

**Tired of losing your Vinted listing photos?** This tool automatically downloads all images and product details (price, size, condition, etc.) from any Vinted item or seller profile. Perfect for re-uploading items!

## ✨ Features
- **Single Item Download**: Grab all photos + details from one listing
- **Bulk Download**: Scrape an entire seller profile at once
- **Automatic Organization**: Creates folders with item names and `description.txt` files
- **Profile Pictures**: Optionally downloads seller profile pictures

## ⚙️ Setup (1 Minute)

### 🐈‍⬛
```bash
git clone https://github.com/im-sofaking/vinted-scraper.git
cd vinted-scraper
```

### 🍎 macOS/Linux
```bash
chmod +x setup.py  # Make setup executable
python3 setup.py   # Run automated setup
```
### 🖥️ Windows
```bash
python setup.py    # Just run the setup directly
```
The script will:

- **Check your Chrome version**
- **Download the matching ChromeDriver**
- **Create a Python virtual environment**
- **Install required packages**

*Note: Requires Python 3.7+ and Google Chrome installed*

### 🐉 Activate virtual environment
```bash
source venv/bin/activate    # To activate virtual environment 
```

## 🚀 Usage 
### Single item:
```bash
python vinted_scraper.py --item="item url"
```
### Profile Mode
```bash
python vinted_scraper.py --all="user url"
```
## ⚠️ Disclaimer
Disclaimer: This Vinted downloader was created to help users back up their own listings for personal reuploading purposes. 
It is not intended for unauthorized scraping, redistribution, or commercial use. I do not endorse or take responsibility for any misuse of this tool. 
All content (images, descriptions, etc.) remains the property of Vinted and its users, and is subject to Vinted's Terms of Service. 
Use at your own discretion.
