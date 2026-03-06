-- 1. DROP the old functions completely
DROP FUNCTION IF EXISTS get_strict_shelters;
DROP FUNCTION IF EXISTS get_fallback_shelters;

-- 2. CREATE Strict Search (with shelter_id integer)
CREATE OR REPLACE FUNCTION get_strict_shelters(
    user_lat double precision,
    user_lng double precision,
    radius_meters integer,
    target_category text,
    user_preference text
)
RETURNS TABLE (
    shelter_id integer,  -- FIXED: Changed from bigint to integer
    name text, shelter_type text, address text, contact_number text, dist_meters double precision, latitude numeric, longitude numeric
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.shelter_id, s.name::text, s.shelter_type::text, s.address::text, s.contact_number::text,
        ST_Distance(ST_SetSRID(ST_MakePoint(s.longitude, s.latitude), 4326)::geography, ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)::geography) AS dist_meters,
        s.latitude, s.longitude
    FROM shelters s
    WHERE 
        ST_DWithin(ST_SetSRID(ST_MakePoint(s.longitude, s.latitude), 4326)::geography, ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)::geography, radius_meters)
        AND (target_category = '' OR s.shelter_type ILIKE '%' || target_category || '%' OR array_to_string(s.target_demographic, ',') ILIKE '%' || target_category || '%')
        AND (user_preference = '' OR s.shelter_type ILIKE '%' || user_preference || '%' OR array_to_string(s.target_demographic, ',') ILIKE '%' || user_preference || '%')
    ORDER BY dist_meters ASC
    LIMIT 8;
END;
$$;

-- 3. CREATE Fallback Search (with shelter_id integer)
CREATE OR REPLACE FUNCTION get_fallback_shelters(
    user_lat double precision,
    user_lng double precision,
    expanded_radius_meters integer,
    target_category text,           
    user_preference text            
)
RETURNS TABLE (
    shelter_id integer,  -- FIXED: Changed from bigint to integer
    name text, shelter_type text, address text, contact_number text, dist_meters double precision, preference_match boolean, latitude numeric, longitude numeric
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.shelter_id, s.name::text, s.shelter_type::text, s.address::text, s.contact_number::text,
        ST_Distance(ST_SetSRID(ST_MakePoint(s.longitude, s.latitude), 4326)::geography, ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)::geography) AS dist_meters,
        (user_preference <> '' AND (s.shelter_type ILIKE '%' || user_preference || '%' OR array_to_string(s.target_demographic, ',') ILIKE '%' || user_preference || '%')) AS preference_match,
        s.latitude, s.longitude
    FROM shelters s
    WHERE 
        ST_DWithin(ST_SetSRID(ST_MakePoint(s.longitude, s.latitude), 4326)::geography, ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)::geography, expanded_radius_meters)
        AND (target_category = '' OR s.shelter_type ILIKE '%' || target_category || '%' OR array_to_string(s.target_demographic, ',') ILIKE '%' || target_category || '%')
    ORDER BY 
        preference_match DESC,
        dist_meters ASC
    LIMIT 8;
END;
$$;