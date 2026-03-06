"""
Migration script to move shelter data from Supabase to DynamoDB
Creates table with geohash GSI and loads shelter_data.json
"""

import boto3
import json
import pygeohash as pgh
from botocore.exceptions import ClientError
from pathlib import Path
import time
import sys
import os
from dotenv import load_dotenv
from decimal import Decimal

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))


# Load environment variables from .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from {env_path}")
else:
    print("Warning: .env file not found, using default AWS credentials")

class ShelterMigration:
    """Migrate shelter data to DynamoDB"""
    
    def __init__(self, table_name: str = "Shelters"):
        region = os.getenv('AWS_REGION', 'us-east-1')
        print(f"Using AWS region: {region}")
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.client = boto3.client('dynamodb', region_name=region)
        self.table_name = table_name
        
    def create_table(self):
        """Create DynamoDB table with geohash GSI"""
        try:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {'AttributeName': 'shelter_id', 'KeyType': 'HASH'}  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'shelter_id', 'AttributeType': 'N'},
                    {'AttributeName': 'geohash6', 'AttributeType': 'S'},
                    {'AttributeName': 'geohash5', 'AttributeType': 'S'},
                    {'AttributeName': 'geohash4', 'AttributeType': 'S'},
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'geohash6-index',
                        'KeySchema': [
                            {'AttributeName': 'geohash6', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'geohash5-index',
                        'KeySchema': [
                            {'AttributeName': 'geohash5', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'geohash4-index',
                        'KeySchema': [
                            {'AttributeName': 'geohash4', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                BillingMode='PROVISIONED',
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            
            print(f"Creating table {self.table_name}...")
            table.wait_until_exists()
            print("Table created successfully!")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"Table {self.table_name} already exists")
                return True
            else:
                print(f"Error creating table: {e}")
                return False
    
    def load_shelter_data(self, json_file_path: str) -> list:
        """Load shelter data from JSON file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                shelters = json.load(f, parse_float=Decimal)
            print(f"Loaded {len(shelters)} shelters from {json_file_path}")
            return shelters
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return []
    
    def add_geohashes(self, shelter: dict) -> dict:
        """Add geohash fields to shelter data"""
        lat = float(shelter['latitude'])
        lon = float(shelter['longitude'])
        
        shelter['geohash4'] = pgh.encode(lat, lon, precision=4)
        shelter['geohash5'] = pgh.encode(lat, lon, precision=5)
        shelter['geohash6'] = pgh.encode(lat, lon, precision=6)
        
        return shelter
    
    def batch_write_shelters(self, shelters: list):
        """Batch write shelters to DynamoDB"""
        table = self.dynamodb.Table(self.table_name)
        
        # Process in batches of 25 (DynamoDB limit)
        batch_size = 25
        total_written = 0
        
        for i in range(0, len(shelters), batch_size):
            batch = shelters[i:i + batch_size]
            
            with table.batch_writer() as writer:
                for shelter in batch:
                    # Add geohashes
                    shelter_with_geohash = self.add_geohashes(shelter)
                    
                    try:
                        writer.put_item(Item=shelter_with_geohash)
                        total_written += 1
                        print(f"✓ Wrote shelter {shelter['shelter_id']}: {shelter['name']}")
                    except Exception as e:
                        print(f"✗ Error writing shelter {shelter['shelter_id']}: {e}")
            
            # Rate limiting
            time.sleep(0.1)
        
        print(f"\nTotal shelters written: {total_written}/{len(shelters)}")
        return total_written
    
    def verify_migration(self) -> bool:
        """Verify migration by checking table item count"""
        try:
            table = self.dynamodb.Table(self.table_name)
            response = table.scan(Select='COUNT')
            count = response['Count']
            
            print(f"\nVerification: {count} items in {self.table_name} table")
            return count > 0
            
        except Exception as e:
            print(f"Verification error: {e}")
            return False
    
    def run_migration(self, json_file_path: str):
        """Run complete migration"""
        print("=" * 60)
        print("Starting Shelter Migration to DynamoDB")
        print("=" * 60)
        
        # Step 1: Create table
        print("\n[Step 1/4] Creating DynamoDB table...")
        if not self.create_table():
            print("Failed to create table. Aborting.")
            return False
        
        # Wait for table to be active
        time.sleep(2)
        
        # Step 2: Load shelter data
        print("\n[Step 2/4] Loading shelter data from JSON...")
        shelters = self.load_shelter_data(json_file_path)
        if not shelters:
            print("No shelter data loaded. Aborting.")
            return False
        
        # Step 3: Write to DynamoDB
        print("\n[Step 3/4] Writing shelters to DynamoDB...")
        total_written = self.batch_write_shelters(shelters)
        
        # Step 4: Verify
        print("\n[Step 4/4] Verifying migration...")
        success = self.verify_migration()
        
        if success:
            print("\n" + "=" * 60)
            print("✓ Migration completed successfully!")
            print("=" * 60)
            print(f"\nYou can now use the DynamoDB shelter service.")
            print(f"Table name: {self.table_name}")
            print(f"Total shelters: {total_written}")
        else:
            print("\n✗ Migration verification failed")
        
        return success


def main():
    """Main migration entry point"""
    # Path to shelter JSON data
    script_dir = Path(__file__).parent
    json_path = script_dir / "shelter_data.json"
    
    if not json_path.exists():
        print(f"Error: shelter_data.json not found at {json_path}")
        return
    
    # Run migration
    migration = ShelterMigration(table_name="Shelters")
    migration.run_migration(str(json_path))


if __name__ == "__main__":
    main()
