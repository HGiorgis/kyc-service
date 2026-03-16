#!/usr/bin/env python
"""
Basic tests for face_recognition functionality using your actual selfie
"""
import face_recognition
import cv2
import numpy as np
from pathlib import Path
import time
import os

def test_face_recognition_with_selfie():
    """Test basic face_recognition functions using your selfie"""
    
    print("=" * 60)
    print("TEST: Face Recognition with Your Selfie")
    print("=" * 60)
    
    # 1. Check version
    print(f"\n📦 face_recognition version: {face_recognition.__version__}")
    
    # 2. Use your actual selfie
    test_path = "D:\\Pictures\\Personal\\selfi.jpg"
    
    # Check if file exists
    if not os.path.exists(test_path):
        print(f"❌ Selfie not found at: {test_path}")
        print("Please check the path or update it to point to your actual selfie")
        return False
    
    print(f"\n🖼️ Using your selfie: {test_path}")
    file_size = os.path.getsize(test_path) / 1024  # KB
    print(f"   File size: {file_size:.1f} KB")
    
    # 3. Load the image
    print("\n📂 Loading image...")
    start_time = time.time()
    image = face_recognition.load_image_file(test_path)
    load_time = time.time() - start_time
    print(f"   Load time: {load_time:.3f}s")
    print(f"   Image shape: {image.shape}")
    
    # 4. Test face detection
    print("\n🔍 Testing face detection...")
    start_time = time.time()
    face_locations = face_recognition.face_locations(image)
    detect_time = time.time() - start_time
    
    if face_locations:
        print(f"✅ Face detected! Found {len(face_locations)} face(s)")
        print(f"   Detection time: {detect_time:.3f}s")
        for i, location in enumerate(face_locations):
            top, right, bottom, left = location
            print(f"   Face {i+1}: Top={top}, Right={right}, Bottom={bottom}, Left={left}")
            print(f"   Face size: {bottom-top} x {right-left} pixels")
    else:
        print("❌ No face detected in your selfie")
        print("   Possible reasons:")
        print("   - Image might be too blurry")
        print("   - Face might be too small")
        print("   - Face might be at an extreme angle")
        return False
    
    # 5. Test face landmarks
    print("\n👁️ Testing face landmarks...")
    start_time = time.time()
    face_landmarks = face_recognition.face_landmarks(image)
    landmarks_time = time.time() - start_time
    
    if face_landmarks:
        print(f"✅ Face landmarks detected!")
        print(f"   Landmarks time: {landmarks_time:.3f}s")
        print(f"   Features found: {list(face_landmarks[0].keys())}")
        
        # Count landmarks per feature
        for feature, points in face_landmarks[0].items():
            print(f"   - {feature}: {len(points)} points")
    else:
        print("❌ No face landmarks detected")
    
    # 6. Test face encodings
    print("\n🔐 Testing face encodings...")
    start_time = time.time()
    face_encodings = face_recognition.face_encodings(image)
    encoding_time = time.time() - start_time
    
    if face_encodings:
        print(f"✅ Face encoding generated!")
        print(f"   Encoding time: {encoding_time:.3f}s")
        print(f"   Encoding shape: {face_encodings[0].shape}")
        print(f"   Encoding sample (first 10 values):")
        print(f"   {face_encodings[0][:10]}")
    else:
        print("❌ No face encoding generated")
        return False
    
    # 7. Additional info
    print("\n📊 Image Information:")
    print(f"   Image dimensions: {image.shape[1]} x {image.shape[0]}")
    print(f"   Color channels: {image.shape[2] if len(image.shape) > 2 else 1}")
    
    # 8. Performance summary
    print("\n⚡ Performance Summary:")
    print(f"   Load time: {load_time:.3f}s")
    print(f"   Detection time: {detect_time:.3f}s")
    print(f"   Landmarks time: {landmarks_time:.3f}s")
    print(f"   Encoding time: {encoding_time:.3f}s")
    print(f"   TOTAL TIME: {load_time + detect_time + landmarks_time + encoding_time:.3f}s")
    
    print("\n✅ Test completed successfully!")
    return True

def test_face_comparison():
    """Test comparing two images (if you have a second image)"""
    
    print("\n" + "=" * 60)
    print("TEST: Face Comparison (Optional)")
    print("=" * 60)
    
    test_path = "D:\\Pictures\\Personal\\selfi.jpg"
    second_image = input("\nEnter path to second image for comparison (or press Enter to skip): ").strip()
    
    if not second_image or not os.path.exists(second_image):
        print("⏩ Skipping face comparison test")
        return
    
    print(f"\n📂 Loading both images...")
    
    # Load first image
    image1 = face_recognition.load_image_file(test_path)
    encodings1 = face_recognition.face_encodings(image1)
    
    if not encodings1:
        print("❌ No face found in first image")
        return
    
    # Load second image
    image2 = face_recognition.load_image_file(second_image)
    encodings2 = face_recognition.face_encodings(image2)
    
    if not encodings2:
        print("❌ No face found in second image")
        return
    
    # Compare faces
    print("\n🔄 Comparing faces...")
    start_time = time.time()
    
    match = face_recognition.compare_faces([encodings1[0]], encodings2[0])[0]
    distance = face_recognition.face_distance([encodings1[0]], encodings2[0])[0]
    similarity = 1 - min(distance, 1.0)
    
    compare_time = time.time() - start_time
    
    print(f"\n📊 Comparison Results:")
    print(f"   Match: {'✅ YES' if match else '❌ NO'}")
    print(f"   Distance: {distance:.3f} (0 = perfect match, >0.6 = different)")
    print(f"   Similarity: {similarity:.1%}")
    print(f"   Time: {compare_time:.3f}s")
    
    if similarity > 0.7:
        print("\n🎉 High confidence match! These are likely the same person.")
    elif similarity > 0.4:
        print("\n⚠️ Moderate confidence - might be the same person under different conditions.")
    else:
        print("\n❌ Low confidence - these are likely different people.")

def test_batch_processing():
    """Test processing multiple images"""
    
    print("\n" + "=" * 60)
    print("TEST: Batch Processing")
    print("=" * 60)
    
    test_path = "D:\\Pictures\\Personal\\selfi.jpg"
    
    # Process the same image multiple times to test performance
    iterations = 5
    
    print(f"\n🔄 Processing same image {iterations} times...")
    
    times = []
    for i in range(iterations):
        start_time = time.time()
        
        image = face_recognition.load_image_file(test_path)
        face_locations = face_recognition.face_locations(image)
        face_encodings = face_recognition.face_encodings(image)
        
        elapsed = time.time() - start_time
        times.append(elapsed)
        print(f"   Iteration {i+1}: {elapsed:.3f}s")
    
    avg_time = sum(times) / len(times)
    print(f"\n📊 Batch Processing Stats:")
    print(f"   Average time: {avg_time:.3f}s")
    print(f"   Min time: {min(times):.3f}s")
    print(f"   Max time: {max(times):.3f}s")

if __name__ == "__main__":
    # Run main test with your selfie
    success = test_face_recognition_with_selfie()
    
    if success:
        # Optional: Run batch test
        print("\n" + "=" * 60)
        choice = input("\nRun batch processing test? (y/n): ").strip().lower()
        if choice == 'y':
            test_batch_processing()
        
        # Optional: Run comparison test
        test_face_comparison()
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)