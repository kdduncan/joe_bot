"""Find the XLS download URL from AEA website."""
import requests
import re

r = requests.get('https://www.aeaweb.org/joe/listings.php', 
                 headers={'User-Agent': 'Mozilla/5.0'}, 
                 timeout=30)

# Search for download-related patterns
patterns = [
    r'href=["\']([^"\']*(?:download|export|xls|xlsx)[^"\']*)["\']',
    r'action=["\']([^"\']*(?:download|export|xls)[^"\']*)["\']',
    r'Native XLS',
    r'Download Options',
]

print("Searching for download patterns...")
for pattern in patterns:
    matches = re.findall(pattern, r.text, re.I)
    if matches:
        print(f"\n{pattern}: {matches[:10]}")

# Also look for any form with XLS
print("\n\nLooking for forms...")
forms = re.findall(r'<form[^>]*>(.*?)</form>', r.text, re.S | re.I)
for i, form in enumerate(forms[:5]):
    if 'xls' in form.lower() or 'download' in form.lower():
        print(f"Form {i}: {form[:500]}...")

# Look for buttons
print("\n\nLooking for buttons with XLS...")
buttons = re.findall(r'<button[^>]*>([^<]*(?:xls|download)[^<]*)</button>', r.text, re.I)
print(f"Buttons: {buttons}")

# Look in the first 50k chars for any download hints
print("\n\nSearching full page for XLS mentions...")
xls_mentions = re.findall(r'.{50}xls.{50}', r.text, re.I)
for x in xls_mentions[:10]:
    print(x)
