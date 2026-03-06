import logging

from models.shelter import ShelterProfile
from models.enums import CrisisCategory
from services.dynamodb_shelter_service import get_shelter_service


class ShelterService:
    def __init__(self):
        self.db_service = get_shelter_service()

    async def find_appropriate_shelters(
        self,
        lat: float,
        lng: float,
        crisis_category: CrisisCategory,
        preferences: str,
    ) -> list[ShelterProfile]:
        target_category = crisis_category.value if crisis_category else ""
        user_pref = preferences if preferences else ""

        logging.info(
            "Executing DynamoDB geohash search (5km+15km) for: %s, Pref: %s",
            target_category,
            user_pref,
        )

        preference_list: list[str] = []
        if target_category:
            preference_list.append(target_category)
        if user_pref:
            preference_list.extend(user_pref.split())

        results = self.db_service.find_appropriate_shelters(
            latitude=lat,
            longitude=lng,
            preferences=preference_list,
            strict_radius_km=5.0,
            fallback_radius_km=15.0,
        )

        shelters_data = results.get("strict", [])
        if not shelters_data:
            logging.warning("Strict match returned 0 results. Using fallback (15km)...")
            shelters_data = results.get("fallback", [])

        raw_shelters: list[ShelterProfile] = []
        for shelter in shelters_data:
            raw_shelters.append(
                ShelterProfile(
                    shelter_id=int(shelter["shelter_id"]),
                    name=shelter["name"],
                    shelter_type=shelter["shelter_type"],
                    address=shelter["address"],
                    contact_number=shelter.get("contact_number"),
                    distance_km=shelter.get("distance_km"),
                    google_maps_url=(
                        "https://www.google.com/maps/search/?api=1&query="
                        f"{shelter['latitude']},{shelter['longitude']}"
                    ),
                )
            )

        return self._rerank_and_truncate(raw_shelters, user_pref)

    def _rerank_and_truncate(
        self,
        shelters: list[ShelterProfile],
        preference: str,
    ) -> list[ShelterProfile]:
        if not shelters:
            return []

        if not preference:
            shelters.sort(key=lambda shelter: shelter.distance_km if shelter.distance_km is not None else 9999)
            return shelters[:4]

        from thefuzz import fuzz

        scored_shelters = []
        max_dist = max([
            shelter.distance_km if shelter.distance_km is not None else 0
            for shelter in shelters
        ])

        for shelter in shelters:
            distance_km = shelter.distance_km if shelter.distance_km is not None else 0
            dist_score = 1.0 - (distance_km / (max_dist + 0.1))
            shelter_text = f"{shelter.name} {shelter.shelter_type}".lower()
            fuzzy_score = fuzz.token_set_ratio(preference.lower(), shelter_text) / 100.0
            final_score = (fuzzy_score * 0.7) + (dist_score * 0.3)
            scored_shelters.append((final_score, shelter))

        scored_shelters.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored_shelters][:4]

    async def find_all_shelters(
        self,
        lat: float,
        lng: float,
        radius_km: int = 25,
    ) -> list[ShelterProfile]:
        try:
            data = self.db_service.find_shelters_by_radius(
                latitude=lat,
                longitude=lng,
                radius_km=float(radius_km),
                is_free=None,
            )

            return [
                ShelterProfile(
                    shelter_id=int(row["shelter_id"]),
                    name=row["name"],
                    shelter_type=row["shelter_type"],
                    address=row["address"],
                    contact_number=row.get("contact_number"),
                    distance_km=row.get("distance_km"),
                    google_maps_url=(
                        "https://www.google.com/maps/search/?api=1&query="
                        f"{row['latitude']},{row['longitude']}"
                    ),
                )
                for row in data
            ]
        except Exception as error:
            logging.error("find_all_shelters error: %s", error)
            return []