import requests
import json
import time
import os

# Your API key from STEP 3
API_KEY = "qdBBs8TSZ8X5oKV51DE0fNVqxDlHPkPyXoZv4Xc9mH0"  # Replace with your actual full key

# Server URL
BASE_URL = "http://127.0.0.1:8000/api/v1"

# Test user ID (use a unique one)
USER_ID = f"test_user_{int(time.time())}"

# Image paths - UPDATE THESE TO YOUR ACTUAL PATHS
ID_FRONT_PATH = r"D:\Pictures\Personal\front.jpg"
ID_BACK_PATH = r"D:\Pictures\Personal\back.jpg"
SELFIE_PATH = r"D:\Pictures\Personal\selfi.jpg"

print("=" * 60)
print("KYC API TEST - SUBMISSION")
print("=" * 60)
print(f"Using API Key: {API_KEY[:8]}...")
print(f"Test User ID: {USER_ID}")
print()

# Check if images exist
for path in [ID_FRONT_PATH, ID_BACK_PATH, SELFIE_PATH]:
    if not os.path.exists(path):
        print(f"❌ Image not found: {path}")
        exit(1)
    print(f"✅ Image found: {path}")

print()

# Test 1: Check initial status (expect 404)
print("📊 Test 1: Check initial status")
url = f"{BASE_URL}/kyc/status/{USER_ID}/"
headers = {"X-API-Key": API_KEY}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")

# Handle response properly
if response.status_code == 404:
    print("✅ Expected: User not found (no KYC submission yet)")
elif response.status_code == 200:
    print(f"Response: {json.dumps(response.json(), indent=2)}")
else:
    try:
        print(f"Response: {response.json()}")
    except:
        print(f"Response text: {response.text}")

print()
input("Press Enter to continue to Test 2 (KYC Submission)...")

# Test 2: Submit KYC
print("\n📤 Test 2: Submit KYC")
url = f"{BASE_URL}/kyc/submit/"

files = {
    'id_front': ('id_front.jpg', open(ID_FRONT_PATH, 'rb'), 'image/jpeg'),
    'id_back': ('id_back.jpg', open(ID_BACK_PATH, 'rb'), 'image/jpeg'),
    'selfie': ('selfie.jpg', open(SELFIE_PATH, 'rb'), 'image/jpeg'),
}

data = {
    'user_id': USER_ID,
    'email': 'juan.martinez@gmail.com',
    'full_name': 'Juan Martinez',
    'id_type': 'national_id',
    'id_number': '1234-5678-9101-5678'
}

print("Sending request...")
start_time = time.time()
response = requests.post(url, headers=headers, files=files, data=data)
elapsed = time.time() - start_time

print(f"Time: {elapsed:.2f}s")
print(f"Status: {response.status_code}")

if response.status_code == 201:
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    SUBMISSION_ID = result.get('submission_id')
    print(f"\n✅ Submission successful!")
    print(f"   Submission ID: {SUBMISSION_ID}")
    print(f"   Status: {result['status']}")
    print(f"   Confidence: {result['confidence']}")
    
    # Close files
    for f in files.values():
        f[1].close()
    
    print()
    input("Press Enter to continue to Test 3 (Check Status After Submission)...")
    
    # Test 3: Check status after submission
    print("\n📊 Test 3: Check status after submission")
    time.sleep(3)  # Wait for processing
    url = f"{BASE_URL}/kyc/status/{USER_ID}/"
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print(f"\n✅ Final Status: {result.get('status')}")
        print(f"   Confidence: {result.get('confidence', 'N/A')}")
    else:
        print(f"❌ Error: {response.status_code}")
        try:
            print(response.json())
        except:
            print(response.text)
            
else:
    print(f"❌ Error: {response.status_code}")
    try:
        print(response.json())
    except:
        print(response.text)
    
    # Close files
    for f in files.values():
        f[1].close()

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)