CREATE TABLE shelters (
  shelter_id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  shelter_type VARCHAR(100),
  target_demographic TEXT[],
  address TEXT,
  contact_number VARCHAR(20),
  latitude DECIMAL(10, 4),
  longitude DECIMAL(10, 4),
  capacity INTEGER,
  services TEXT[],
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shelter_type ON shelters(shelter_type);
CREATE INDEX idx_location ON shelters(latitude, longitude);

-- Add is_free column to existing shelters table
ALTER TABLE shelters ADD COLUMN is_free BOOLEAN DEFAULT TRUE;
UPDATE shelters SET is_free = TRUE WHERE is_free IS NULL;
CREATE INDEX idx_is_free ON shelters(is_free);