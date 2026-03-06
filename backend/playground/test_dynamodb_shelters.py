"""
Test script for DynamoDB shelter service migration
Run this after executing migrate_shelters_to_dynamodb.py
"""

import sys
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.dynamodb_shelter_service import get_shelter_service
from models.enums import CrisisCategory


def test_basic_search():
    """Test basic radius search"""
    print("\n" + "=" * 60)
    print("Test 1: Basic Radius Search (Bengaluru Central)")
    print("=" * 60)
    
    service = get_shelter_service()
    
    # Bengaluru city center coordinates
    lat, lon = 12.9716, 77.5946
    
    # Find shelters within 5km
    shelters = service.find_shelters_by_radius(lat, lon, radius_km=5.0, is_free=True)
    
    print(f"\nFound {len(shelters)} free shelters within 5km:")
    for shelter in shelters[:5]:
        print(f"  - {shelter['name']}")
        print(f"    Type: {shelter['shelter_type']}")
        print(f"    Distance: {shelter['distance_km']} km")
        print(f"    Contact: {shelter.get('contact_number', 'N/A')}")
        print()


def test_preference_search():
    """Test preference-based search"""
    print("\n" + "=" * 60)
    print("Test 2: Preference-Based Search (Domestic Violence)")
    print("=" * 60)
    
    service = get_shelter_service()
    
    # HSR Layout coordinates
    lat, lon = 12.9116, 77.6389
    
    preferences = ["domestic_violence", "women", "counseling"]
    
    results = service.find_appropriate_shelters(
        latitude=lat,
        longitude=lon,
        preferences=preferences,
        strict_radius_km=5.0,
        fallback_radius_km=15.0
    )
    
    print(f"\nStrict Search Results (5km, free only):")
    strict = results['strict']
    if strict:
        for shelter in strict[:3]:
            print(f"  - {shelter['name']}")
            print(f"    Match Score: {shelter['match_score']:.2f}")
            print(f"    Distance: {shelter['distance_km']} km")
            print(f"    Demographics: {', '.join(shelter.get('target_demographic', []))}")
            print()
    else:
        print("  No strict matches found")
    
    print(f"\nFallback Search Results (15km, all shelters):")
    fallback = results['fallback']
    if fallback:
        for shelter in fallback[:3]:
            print(f"  - {shelter['name']}")
            print(f"    Match Score: {shelter['match_score']:.2f}")
            print(f"    Distance: {shelter['distance_km']} km")
            print(f"    Free: {shelter.get('is_free', False)}")
            print()


def test_large_radius():
    """Test large radius search"""
    print("\n" + "=" * 60)
    print("Test 3: Large Radius Search (25km from Whitefield)")
    print("=" * 60)
    
    service = get_shelter_service()
    
    # Whitefield coordinates
    lat, lon = 12.9698, 77.7499
    
    shelters = service.find_shelters_by_radius(lat, lon, radius_km=25.0)
    
    print(f"\nFound {len(shelters)} shelters within 25km")
    
    # Group by shelter type
    by_type = {}
    for shelter in shelters:
        stype = shelter['shelter_type']
        by_type[stype] = by_type.get(stype, 0) + 1
    
    print("\nBreakdown by shelter type:")
    for stype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {stype}: {count}")


def test_get_by_id():
    """Test getting shelter by ID"""
    print("\n" + "=" * 60)
    print("Test 4: Get Shelter by ID")
    print("=" * 60)
    
    service = get_shelter_service()
    
    # Test with Sakhi One Stop Centre (ID 101)
    shelter = service.get_shelter_by_id(101)
    
    if shelter:
        print(f"\nShelter Details:")
        print(f"  ID: {shelter['shelter_id']}")
        print(f"  Name: {shelter['name']}")
        print(f"  Type: {shelter['shelter_type']}")
        print(f"  Address: {shelter['address']}")
        print(f"  Contact: {shelter.get('contact_number')}")
        print(f"  Coordinates: {shelter['latitude']}, {shelter['longitude']}")
        print(f"  Capacity: {shelter['capacity']}")
        print(f"  Services: {', '.join(shelter.get('services', []))}")
        print(f"  Demographics: {', '.join(shelter.get('target_demographic', []))}")
        print(f"  Geohash (6): {shelter.get('geohash6')}")
    else:
        print("  Shelter not found!")


def test_geohash_precision():
    """Test different geohash precision levels"""
    print("\n" + "=" * 60)
    print("Test 5: Geohash Precision Analysis")
    print("=" * 60)
    
    service = get_shelter_service()
    
    # Test from city center
    lat, lon = 12.9716, 77.5946
    
    for radius in [2, 5, 10, 20]:
        shelters = service.find_shelters_by_radius(lat, lon, radius_km=radius)
        print(f"  Radius {radius}km: {len(shelters)} shelters found")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(" DynamoDB Shelter Service Test Suite")
    print("=" * 70)
    
    try:
        test_basic_search()
        test_preference_search()
        test_large_radius()
        test_get_by_id()
        test_geohash_precision()
        
        print("\n" + "=" * 70)
        print("✓ All tests completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
