-- 1️⃣ ENUMS (additions: drink_type, interaction_type)
CREATE TYPE drink_type AS ENUM (
  'espresso', 'cold_brew', 'latte', 'cappuccino', 'americano', 'filter', 'other'
);
CREATE TYPE interaction_type AS ENUM (
  'view', 'click', 'add_to_favorites', 'purchase', 'other'
);

-- 2️⃣ Cafés & Locations
-- “cafes” now holds the brand‐level info; “cafe_locations” holds each physical spot.
CREATE TABLE cafes (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  description TEXT,
  website     TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cafe_locations (
  id          SERIAL PRIMARY KEY,
  cafe_id     INT REFERENCES cafes(id) ON DELETE CASCADE,
  address     TEXT NOT NULL,
  city        TEXT,
  state       TEXT,
  country     TEXT,
  postal_code TEXT,
  lat         NUMERIC,      -- optional for future geo
  lon         NUMERIC,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- 3️⃣ Beans (unchanged)
CREATE TABLE beans (
  id                    SERIAL PRIMARY KEY,
  name                  TEXT NOT NULL,
  weight_g              REAL,
  price_usd             REAL,
  proprietor            TEXT,
  region_country        TEXT,
  region_area           TEXT,
  roast_level           roast_level,
  flavor_notes          TEXT[],        
  grind_type            grind_type,
  created_at            TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE bean_specialties (
  bean_id               INT PRIMARY KEY REFERENCES beans(id) ON DELETE CASCADE,
  farm                  TEXT,
  altitude_masl         INT,
  process               bean_process,
  agtron_roast_level    INT,
  suitable_brew_types   brewing_method[],
  bean_type             bean_type,
  variety               TEXT
);

-- 4️⃣ Menu Items tied to a specific location, with drink type
CREATE TABLE menu_items (
  id            SERIAL PRIMARY KEY,
  location_id   INT REFERENCES cafe_locations(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  description   TEXT,
  price_usd     REAL,
  drink_type    drink_type,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- 5️⃣ Availability mappings at the location level
CREATE TABLE cafe_location_beans (
  location_id   INT REFERENCES cafe_locations(id) ON DELETE CASCADE,
  bean_id       INT REFERENCES beans(id) ON DELETE CASCADE,
  PRIMARY KEY(location_id, bean_id)
);

-- 6️⃣ Users & Preferences (unchanged)
CREATE TABLE users (
  id              SERIAL PRIMARY KEY,
  first_name      TEXT NOT NULL,
  last_name       TEXT NOT NULL,
  username        TEXT NOT NULL UNIQUE,
  email           TEXT NOT NULL UNIQUE,
  dob             DATE,
  budget_range    budget_range,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_preferences (
  user_id                  INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  brewing_method           brewing_method,
  roast_level_pref         roast_level,
  consumption_frequency    consumption_frequency,
  flavor_or_caffeine_pref  flavor_or_caffeine_pref
);

CREATE TABLE user_flavor_preferences (
  user_id   INT REFERENCES users(id) ON DELETE CASCADE,
  flavor    flavor_note,
  PRIMARY KEY (user_id, flavor)
);

-- 7️⃣ Likes (unchanged, but beans and cafes now at location-level for cafes)
CREATE TABLE user_liked_beans (
  user_id   INT REFERENCES users(id) ON DELETE CASCADE,
  bean_id   INT REFERENCES beans(id) ON DELETE CASCADE,
  liked_at  TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, bean_id)
);

CREATE TABLE user_liked_locations (
  user_id    INT REFERENCES users(id) ON DELETE CASCADE,
  location_id INT REFERENCES cafe_locations(id) ON DELETE CASCADE,
  liked_at    TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, location_id)
);

-- 8️⃣ Browsing / Interaction Tracking
CREATE TABLE user_interactions (
  id             BIGSERIAL PRIMARY KEY,
  user_id        INT REFERENCES users(id) ON DELETE CASCADE,
  interaction    interaction_type NOT NULL,
  object_type    TEXT NOT NULL,         -- e.g. 'bean', 'location', 'menu_item'
  object_id      INT NOT NULL,
  metadata       JSONB,                 -- e.g. { "session_id": "...", "referrer": "...", "duration_s": 12 }
  occurred_at    TIMESTAMPTZ DEFAULT now()
);
