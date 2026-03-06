import logging
import time
from supabase import create_client, Client
from thefuzz import fuzz

from config.config import get_settings
from models.shelter import ShelterProfile
from models.enums import CrisisCategory


def _rpc_with_retry(supabase: Client, fn_name: str, params: dict, max_retries: int = 3) -> list:
    """Execute a Supabase RPC call with retry on HTTP/2 connection errors."""
    for attempt in range(1, max_retries + 1):
        try:
            response = supabase.rpc(fn_name, params).execute()
            return response.data or []
        except Exception as e:
            err_str = str(e).lower()
            is_retryable = any(kw in err_str for kw in [
                "connectionterminated", "remoteprotocolerror", "connectionreset",
                "connection", "reset", "broken", "eof", "closed",
            ])
            if is_retryable and attempt < max_retries:
                wait = 0.5 * attempt
                logging.warning(f"[SUPABASE] {fn_name} attempt {attempt} failed ({e}). Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logging.error(f"[SUPABASE] {fn_name} failed after {attempt} attempt(s): {e}")
                raise

class ShelterService:
    def __init__(self):
        settings = get_settings()
        
        self.supabase: Client = create_client(
            settings.supabase.url, 
            settings.supabase.service_key
        )

    async def find_appropriate_shelters(
        self, 
        lat: float, 
        lng: float, 
        crisis_category: CrisisCategory, 
        preferences: str
    ) -> list[ShelterProfile]:
        """
        Executes the Strict 5km Search. If empty, falls back to the 15km Soft Search.
        """
        target_category = crisis_category.value if crisis_category else ""
        user_pref = preferences if preferences else ""
        
        logging.info(f"Executing STRICT Supabase RPC (5km) for: {target_category}, Pref: {user_pref}")
        
        # 1. Try Strict Match (5km, Exact Category, Exact Preference)
        shelters_data = _rpc_with_retry(self.supabase, 'get_strict_shelters_free', {
            'user_lat': lat,
            'user_lng': lng,
            'radius_meters': 5000,
            'target_category': target_category,
            'user_preference': user_pref
        })

        # 2. Trigger Fallback if Strict Fails (15km, Soft Preference Ranking)
        if not shelters_data:
            logging.warning("Strict match returned 0 results. Triggering FALLBACK RPC (15km)...")
            shelters_data = _rpc_with_retry(self.supabase, 'get_fallback_shelters_free', {
                'user_lat': lat,
                'user_lng': lng,
                'expanded_radius_meters': 15000,
                'target_category': target_category,
                'user_preference': user_pref
            })

        # 3. Map Raw DB Dictionaries to Pydantic Models
        raw_shelters =[]
        if shelters_data:
            for s in shelters_data:
                raw_shelters.append(ShelterProfile(
                    shelter_id=s['shelter_id'],
                    name=s['name'],
                    shelter_type=s['shelter_type'],
                    address=s['address'],
                    contact_number=s.get('contact_number'),
                    # Convert meters to km and round to 2 decimals
                    distance_km=round(s['dist_meters'] / 1000, 2),
                    google_maps_url=f"https://www.google.com/maps/search/?api=1&query={s['latitude']},{s['longitude']}"
                ))
                
        return self._rerank_and_truncate(raw_shelters, user_pref)

    def _rerank_and_truncate(self, shelters: list[ShelterProfile], preference: str) -> list[ShelterProfile]:
        """
        Hybrid Scoring: Combines Spatial Distance and Fuzzy Semantic Matching.
        Returns strictly the Top 4.
        """
        if not shelters:
            return[]

        # If no preference provided, just return the 4 closest.
        if not preference:
            shelters.sort(key=lambda x: x.distance_km)
            return shelters[:4]

        scored_shelters =[]
        max_dist = max([s.distance_km for s in shelters])
        
        for shelter in shelters:
            dist_score = 1.0 - (shelter.distance_km / (max_dist + 0.1))

            # We compare the user's preference string against the shelter's name and type
            shelter_text = f"{shelter.name} {shelter.shelter_type}".lower()
            
            fuzzy_score = fuzz.token_set_ratio(preference.lower(), shelter_text) / 100.0

            # Safety/Preference is usually more critical than an extra 1km of travel.
            # Weighting: 70% Preference Match, 30% Distance Match
            final_score = (fuzzy_score * 0.7) + (dist_score * 0.3)
            
            scored_shelters.append((final_score, shelter))

        scored_shelters.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_shelters][:4]
    
    async def find_all_shelters(self, lat: float, lng: float, radius_km: int = 25) -> list[ShelterProfile]:
        """Get ALL shelters within radius, regardless of category"""
        try:
            data = _rpc_with_retry(self.supabase, 'get_fallback_shelters_free', {
                'user_lat': lat,
                'user_lng': lng,
                'expanded_radius_meters': radius_km * 1000,
                'target_category': '',  # Empty = match all
                'user_preference': ''
            })
            
            if data:
                return [
                    ShelterProfile(
                        shelter_id=row['shelter_id'],
                        name=row['name'],
                        shelter_type=row['shelter_type'],
                        address=row['address'],
                        contact_number=row['contact_number'],
                        distance_km=round(row['dist_meters'] / 1000, 2) if row.get('dist_meters') else None,
                        google_maps_url=f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}"
                    )
                    for row in data
                ]
            return []
        except Exception as e:
            print(f"❌ find_all_shelters error: {e}")
            return []