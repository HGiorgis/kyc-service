import requests
import json
import time
import os

API_KEY = "jg79IoRGQYQT0PFO-8Vyp3C-od1tH9tcqI1TjMN80mA"
BASE_URL = "http://127.0.0.1:8000/api/v1"

# Use a NEW unique ID
USER_ID = f"juan_martinez_real_{int(time.time())}"

# ✅ EXACT DATA FROM OCR (COPY THESE EXACTLY)
REAL_ID_NUMBER = "000010123456"      # From back of ID
REAL_FULL_NAME = "JUAN MARTINEZ"      # From front of ID
REAL_ID_TYPE = "national_id"          # This is a Philippine National ID

print("=" * 60)
print("KYC TEST WITH EXACT OCR DATA")
print("=" * 60)
print(f"User ID: {USER_ID}")
print(f"ID Type: {REAL_ID_TYPE}")
print(f"ID Number: {REAL_ID_NUMBER}")
print(f"Full Name: {REAL_FULL_NAME}")
print()

headers = {"X-API-Key": API_KEY}

# Submit KYC
submit_url = f"{BASE_URL}/kyc/submit/"

files = {
    'id_front': ('front.jpg', open(r"D:\Pictures\Personal\front.jpg", 'rb'), 'image/jpeg'),
    'id_back': ('back.jpg', open(r"D:\Pictures\Personal\back.jpg", 'rb'), 'image/jpeg'),
    'selfie': ('selfie.jpg', open(r"D:\Pictures\Personal\selfi.jpg", 'rb'), 'image/jpeg'),
}

data = {
    'user_id': USER_ID,
    'email': 'juan.martinez@email.com',
    'full_name': REAL_FULL_NAME,
    'id_type': REAL_ID_TYPE,
    'id_number': REAL_ID_NUMBER
}

print("📤 Submitting with EXACT OCR data...")
response = requests.post(submit_url, headers=headers, files=files, data=data)

print(f"Status: {response.status_code}")
result = response.json()
print(f"Response: {json.dumps(result, indent=2)}")

if response.status_code == 201:
    print(f"\n✅ Submission ID: {result['submission_id']}")
    print(f"✅ Status: {result['status']}")
    print(f"✅ Confidence: {result['confidence']}")
    
    # Check status after processing
    print("\n⏳ Waiting 10 seconds for processing...")
    time.sleep(10)
    
    status_url = f"{BASE_URL}/kyc/status/{USER_ID}/"
    response = requests.get(status_url, headers=headers)
    print(f"\n📊 Final Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

# Close files
for f in files.values():
    f[1].close()