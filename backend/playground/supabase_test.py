import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
load_dotenv()

from services.shelter_service import ShelterService
from models.enums import CrisisCategory

async def test_shelter_service():
    """Test ShelterService with realistic inputs matching actual data"""
    
    print("=" * 60)
    print("🏠 SHELTER SERVICE TEST")
    print("=" * 60)
    
    # Initialize service
    try:
        service = ShelterService()
        print("✅ ShelterService initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize ShelterService: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test cases based on ACTUAL shelter_data.json
    # Using real coordinates from your data and matching target_demographics
    test_cases = [
        {
            "name": "Domestic Violence - Near Sakhi One Stop Centre",
            "lat": 12.9716,  # Same as shelter_id 101
            "lng": 77.5946,
            "crisis": CrisisCategory.DOMESTIC_VIOLENCE,  # matches target_demographic
            "preference": "women only"  # fuzzy matches "Women Only / Domestic Violence"
        },
        {
            "name": "Illegal Eviction - Near JC Road Shelter",
            "lat": 12.9632,  # Same as shelter_id 102
            "lng": 77.5855,
            "crisis": CrisisCategory.ILLEGAL_EVICTION,
            "preference": ""  # No specific preference, looking for general shelter
        },
        {
            "name": "Natural Disaster - General Homeless",
            "lat": 12.9767,  # Near Goods Shed Road shelter
            "lng": 77.5713,
            "crisis": CrisisCategory.NATURAL_DISASTER,  # matches target_demographic in data
            "preference": "homeless"
        },
        {
            "name": "No Preference - Closest Shelter",
            "lat": 12.9716,
            "lng": 77.5946,
            "crisis": CrisisCategory.ILLEGAL_EVICTION,
            "preference": ""
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {test['name']}")
        print(f"{'='*60}")
        print(f"📍 Location: ({test['lat']}, {test['lng']})")
        print(f"🆘 Crisis Category: {test['crisis'].value}")
        print(f"🔍 User Preference: '{test['preference']}'\n")
        
        print("📤 RPC Call Parameters:")
        print(f"   user_lat: {test['lat']}")
        print(f"   user_lng: {test['lng']}")
        print(f"   radius_meters: 5000 (strict) / 15000 (fallback)")
        print(f"   target_category: '{test['crisis'].value}'")
        print(f"   user_preference: '{test['preference']}'\n")
        
        try:
            shelters = await service.find_appropriate_shelters(
                lat=test['lat'],
                lng=test['lng'],
                crisis_category=test['crisis'],
                preferences=test['preference']
            )
            
            if shelters:
                print(f"✅ Found {len(shelters)} shelter(s):\n")
                for idx, shelter in enumerate(shelters, 1):
                    print(f"   {idx}. {shelter.name}")
                    print(f"      Type: {shelter.shelter_type}")
                    print(f"      Distance: {shelter.distance_km} km")
                    print(f"      Address: {shelter.address}")
                    print(f"      Contact: {shelter.contact_number}")
                    print(f"      Maps: {shelter.google_maps_url}")
                    print()
            else:
                print("⚠️ No shelters found matching criteria\n")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    # Debug: Show what RPC actually receives
    print("\n" + "="*60)
    print("🔧 DEBUG: Raw RPC Test")
    print("="*60)
    
    try:
        # Direct RPC call to see raw response
        response = service.supabase.rpc(
            'get_strict_shelters',
            {
                'user_lat': 12.9716,
                'user_lng': 77.5946,
                'radius_meters': 5000,
                'target_category': 'domestic_violence',
                'user_preference': 'women only'
            }
        ).execute()
        
        print(f"\n📥 Raw RPC Response:")
        print(f"   Data type: {type(response.data)}")
        print(f"   Data length: {len(response.data) if response.data else 0}")
        if response.data:
            print(f"   First record: {response.data[0]}")
        else:
            print("   No data returned from strict search")
            
            # Try fallback
            print("\n   Trying fallback RPC...")
            fallback = service.supabase.rpc(
                'get_fallback_shelters',
                {
                    'user_lat': 12.9716,
                    'user_lng': 77.5946,
                    'expanded_radius_meters': 15000,
                    'target_category': 'domestic_violence',
                    'user_preference': 'women only'
                }
            ).execute()
            print(f"   Fallback data length: {len(fallback.data) if fallback.data else 0}")
            if fallback.data:
                print(f"   First fallback record: {fallback.data[0]}")
                
    except Exception as e:
        print(f"❌ Raw RPC failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Interactive mode
    print("\n" + "="*60)
    print("🎯 INTERACTIVE MODE")
    print("="*60)
    print("Test with custom inputs or type 'exit' to quit\n")
    
    # Show available crisis categories
    print("Available CrisisCategory values:")
    for cat in CrisisCategory:
        print(f"  - {cat.value}")
    print()
    
    while True:
        try:
            user_input = input("Enter latitude (or 'exit'): ").strip()
            if user_input.lower() == 'exit':
                break
            
            user_lat = float(user_input)
            user_lng = float(input("Enter longitude: ").strip())
            
            crisis_input = input("Enter crisis category (from list above): ").strip()
            
            # Match crisis category
            crisis_cat = None
            for cat in CrisisCategory:
                if cat.value.lower() == crisis_input.lower():
                    crisis_cat = cat
                    break
            
            if not crisis_cat:
                print(f"⚠️ Unknown category '{crisis_input}'. Using ILLEGAL_EVICTION.\n")
                crisis_cat = CrisisCategory.ILLEGAL_EVICTION
            
            preference = input("Enter preference (or leave blank): ").strip()
            
            print("\n🔍 Searching with:")
            print(f"   target_category: '{crisis_cat.value}'")
            print(f"   user_preference: '{preference}'\n")
            
            shelters = await service.find_appropriate_shelters(
                lat=user_lat,
                lng=user_lng,
                crisis_category=crisis_cat,
                preferences=preference
            )
            
            if shelters:
                print(f"✅ Found {len(shelters)} shelter(s):\n")
                for idx, shelter in enumerate(shelters, 1):
                    print(f"   {idx}. {shelter.name} ({shelter.distance_km} km)")
                    print(f"      Type: {shelter.shelter_type}")
                    print()
            else:
                print("⚠️ No shelters found\n")
                
        except ValueError as e:
            print(f"❌ Invalid input: {e}\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_shelter_service())