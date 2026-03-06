"""
DynamoDB-based Shelter Service with Geohashing for Spatial Queries
Replaces Supabase PostGIS with DynamoDB + geohash indexing
"""

import boto3
import pygeohash as pgh
from typing import List, Dict, Optional, Tuple
from thefuzz import fuzz
from botocore.exceptions import ClientError
import logging
import math
import os
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from backend/.env when available
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


class DynamoDBShelterService:
    """
    DynamoDB shelter service using geohashing for spatial queries.
    
    Table Design:
    - Primary Key: shelter_id (Number)
    - GSI: geohash6-index (geohash6 as partition key)
    - Attributes: name, shelter_type, target_demographic (List), 
                  latitude, longitude, geohash4, geohash5, geohash6,
                  address, contact_number, capacity, services (List), is_free
    """
    
    def __init__(self, table_name: str = "Shelters"):
        """Initialize DynamoDB shelter service"""
        region = os.getenv('AWS_REGION', 'us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
        
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.
        Returns distance in kilometers.
        """
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _get_geohash_neighbors(self, geohash: str) -> List[str]:
        """Get all neighboring geohashes (9 total including center)"""
        neighbors = [geohash]
        try:
            # Get 8 neighbors (N, NE, E, SE, S, SW, W, NW)
            neighbors.extend([
                pgh.get_adjacent(geohash, 'top'),
                pgh.get_adjacent(pgh.get_adjacent(geohash, 'top'), 'right'),
                pgh.get_adjacent(geohash, 'right'),
                pgh.get_adjacent(pgh.get_adjacent(geohash, 'bottom'), 'right'),
                pgh.get_adjacent(geohash, 'bottom'),
                pgh.get_adjacent(pgh.get_adjacent(geohash, 'bottom'), 'left'),
                pgh.get_adjacent(geohash, 'left'),
                pgh.get_adjacent(pgh.get_adjacent(geohash, 'top'), 'left'),
            ])
        except Exception as e:
            logger.warning(f"Failed to get geohash neighbors: {e}")
        
        return neighbors
    
    def _query_by_geohash(self, geohash: str, max_distance_km: float,
                          user_lat: float, user_lon: float,
                          geohash_precision: int) -> List[Dict]:
        """Query shelters by geohash and filter by distance"""
        shelters = []

        if geohash_precision == 6:
            index_name = 'geohash6-index'
            geohash_key = 'geohash6'
        elif geohash_precision == 5:
            index_name = 'geohash5-index'
            geohash_key = 'geohash5'
        else:
            index_name = 'geohash4-index'
            geohash_key = 'geohash4'
        
        try:
            response = self.table.query(
                IndexName=index_name,
                KeyConditionExpression=f'{geohash_key} = :gh',
                ExpressionAttributeValues={':gh': geohash}
            )
            
            # Filter by actual distance
            for item in response.get('Items', []):
                distance = self._calculate_distance(
                    user_lat, user_lon,
                    float(item['latitude']), float(item['longitude'])
                )
                
                if distance <= max_distance_km:
                    item['distance_km'] = round(distance, 2)
                    shelters.append(item)
                    
        except ClientError as e:
            logger.error(f"DynamoDB query error for geohash {geohash}: {e}")
        
        return shelters
    
    def find_shelters_by_radius(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        is_free: Optional[bool] = None
    ) -> List[Dict]:
        """
        Find shelters within radius using geohash search.
        
        Args:
            latitude: User's latitude
            longitude: User's longitude
            radius_km: Search radius in kilometers
            is_free: Filter by free shelters (optional)
            
        Returns:
            List of shelters sorted by distance
        """
        # Determine geohash precision based on radius
        # geohash6 ≈ 600m x 1200m, geohash5 ≈ 5km x 5km, geohash4 ≈ 20km x 40km
        if radius_km <= 5:
            geohash_precision = 6
        elif radius_km <= 15:
            geohash_precision = 5
        else:
            geohash_precision = 4
        
        # Get user's geohash and neighbors
        user_geohash = pgh.encode(latitude, longitude, precision=geohash_precision)
        search_geohashes = self._get_geohash_neighbors(user_geohash)
        
        logger.info(f"Searching {len(search_geohashes)} geohashes at precision {geohash_precision}")
        
        # Query all geohash cells
        all_shelters = []
        for gh in search_geohashes:
            shelters = self._query_by_geohash(
                gh,
                radius_km,
                latitude,
                longitude,
                geohash_precision
            )
            all_shelters.extend(shelters)
        
        # Deduplicate by shelter_id
        unique_shelters = {s['shelter_id']: s for s in all_shelters}.values()
        
        # Filter by is_free if specified
        if is_free is not None:
            unique_shelters = [s for s in unique_shelters if s.get('is_free') == is_free]
        
        # Sort by distance
        sorted_shelters = sorted(unique_shelters, key=lambda x: x['distance_km'])
        
        logger.info(f"Found {len(sorted_shelters)} shelters within {radius_km}km")
        return sorted_shelters
    
    def _calculate_preference_score(
        self,
        shelter: Dict,
        preferences: List[str]
    ) -> float:
        """
        Calculate preference match score using fuzzy matching.
        Returns score between 0 and 1.
        """
        if not preferences:
            return 1.0
        
        # Combine all searchable text
        shelter_text = " ".join([
            shelter.get('shelter_type', ''),
            " ".join(shelter.get('target_demographic', [])),
            " ".join(shelter.get('services', []))
        ]).lower()
        
        # Calculate fuzzy match scores
        scores = []
        for pref in preferences:
            pref_lower = pref.lower()
            # Check for exact substring match first
            if pref_lower in shelter_text:
                scores.append(100)
            else:
                # Use fuzzy matching
                score = fuzz.partial_ratio(pref_lower, shelter_text)
                scores.append(score)
        
        # Average score normalized to 0-1
        return sum(scores) / (len(scores) * 100) if scores else 0.0
    
    def find_appropriate_shelters(
        self,
        latitude: float,
        longitude: float,
        preferences: Optional[List[str]] = None,
        strict_radius_km: float = 5.0,
        fallback_radius_km: float = 15.0
    ) -> Dict:
        """
        Find appropriate shelters with two-tier search (strict + fallback).
        
        Args:
            latitude: User's latitude
            longitude: User's longitude
            preferences: List of preference keywords (demographics, services, etc.)
            strict_radius_km: First tier search radius (default 5km)
            fallback_radius_km: Second tier search radius (default 15km)
            
        Returns:
            Dict with 'strict' and 'fallback' shelter lists, each with scored results
        """
        preferences = preferences or []
        
        # Tier 1: Strict search (5km, free only)
        strict_shelters = self.find_shelters_by_radius(
            latitude, longitude, strict_radius_km, is_free=True
        )
        
        # Score and sort by combined preference + distance
        for shelter in strict_shelters:
            pref_score = self._calculate_preference_score(shelter, preferences)
            distance_score = 1.0 - min(shelter['distance_km'] / strict_radius_km, 1.0)
            
            # 70% preference, 30% distance
            shelter['match_score'] = (0.7 * pref_score + 0.3 * distance_score)
            shelter['preference_score'] = round(pref_score, 2)
        
        strict_shelters.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Tier 2: Fallback search (15km, include paid)
        fallback_shelters = self.find_shelters_by_radius(
            latitude, longitude, fallback_radius_km, is_free=None
        )
        
        # Score fallback shelters
        for shelter in fallback_shelters:
            pref_score = self._calculate_preference_score(shelter, preferences)
            distance_score = 1.0 - min(shelter['distance_km'] / fallback_radius_km, 1.0)
            
            shelter['match_score'] = (0.7 * pref_score + 0.3 * distance_score)
            shelter['preference_score'] = round(pref_score, 2)
        
        fallback_shelters.sort(key=lambda x: x['match_score'], reverse=True)
        
        return {
            'strict': strict_shelters[:10],  # Top 10 strict matches
            'fallback': fallback_shelters[:10]  # Top 10 fallback matches
        }
    
    def get_shelter_by_id(self, shelter_id: int) -> Optional[Dict]:
        """Get shelter details by ID"""
        try:
            response = self.table.get_item(Key={'shelter_id': shelter_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error fetching shelter {shelter_id}: {e}")
            return None
    
    def list_all_shelters(self, limit: int = 100) -> List[Dict]:
        """List all shelters (for admin purposes)"""
        try:
            response = self.table.scan(Limit=limit)
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error scanning shelters: {e}")
            return []


# Singleton instance
_shelter_service = None


def get_shelter_service() -> DynamoDBShelterService:
    """Get or create shelter service singleton"""
    global _shelter_service
    if _shelter_service is None:
        _shelter_service = DynamoDBShelterService()
    return _shelter_service
