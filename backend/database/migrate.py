import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client
from config.config import get_settings

def migrate_shelters():
    """Migrate shelter_data.json to Supabase"""
    
    print("=" * 60)
    print("🚀 MIGRATING SHELTER DATA TO SUPABASE")
    print("=" * 60)
    
    # Initialize Supabase client
    settings = get_settings()
    supabase: Client = create_client(
        settings.supabase.url, 
        settings.supabase.service_key
    )
    
    # Load JSON data
    json_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'shelter_data.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        shelters = json.load(f)
    
    print(f"\n📂 Loaded {len(shelters)} shelters from JSON\n")
    
    # Clear existing data (optional)
    clear = input("Clear existing shelter data? (y/n): ").strip().lower()
    if clear == 'y':
        try:
            supabase.table("shelters").delete().neq("shelter_id", 0).execute()
            print("✅ Cleared existing data\n")
        except Exception as e:
            print(f"⚠️ Could not clear data: {e}\n")
    
    # Insert each shelter
    success_count = 0
    error_count = 0
    
    for shelter in shelters:
        try:
            response = supabase.table("shelters").insert({
                "shelter_id": shelter["shelter_id"],
                "name": shelter["name"],
                "shelter_type": shelter["shelter_type"],
                "target_demographic": shelter["target_demographic"],
                "address": shelter["address"],
                "contact_number": shelter["contact_number"],
                "latitude": shelter["latitude"],
                "longitude": shelter["longitude"],
                "capacity": shelter["capacity"],
                "services": shelter["services"]
            }).execute()
            
            print(f"✅ Inserted: {shelter['name']}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Failed: {shelter['name']} - {e}")
            error_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MIGRATION SUMMARY")
    print("=" * 60)
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {error_count}")
    print(f"📦 Total: {len(shelters)}")
    
    # Verify
    print("\n🔍 Verifying data in Supabase...")
    response = supabase.table("shelters").select("shelter_id, name").execute()
    print(f"✅ Found {len(response.data)} shelters in database")

def import_shelters():
    """Import shelter_data.json into Supabase"""
    
    print("=" * 60)
    print("📥 IMPORTING SHELTER DATA TO SUPABASE")
    print("=" * 60)
    
    settings = get_settings()
    supabase: Client = create_client(settings.supabase.url, settings.supabase.service_key)
    
    # Load JSON
    json_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'shelter_data.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        shelters = json.load(f)
    
    print(f"\n📋 Found {len(shelters)} shelters in JSON\n")
    
    # Clear existing data (optional)
    clear = input("Clear existing shelters? (y/n): ").strip().lower()
    if clear == 'y':
        supabase.table("shelters").delete().neq("shelter_id", 0).execute()
        print("🗑️ Cleared existing data\n")
    
    # Insert each shelter
    success = 0
    failed = 0
    
    for shelter in shelters:
        try:
            # Ensure is_free field exists (default True)
            if 'is_free' not in shelter:
                shelter['is_free'] = True
                
            supabase.table("shelters").upsert(shelter).execute()
            free_status = "🆓" if shelter.get('is_free', True) else "💰"
            print(f"✅ {free_status} {shelter['name']}")
            success += 1
        except Exception as e:
            print(f"❌ {shelter['name']}: {e}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"✅ Imported: {success}")
    print(f"❌ Failed: {failed}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    migrate_shelters()
    import_shelters()