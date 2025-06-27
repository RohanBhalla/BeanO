-- 1️⃣ ENUMS (additions: drink_type, interaction_type, currency)
CREATE TYPE drink_type AS ENUM (
  'espresso', 'cold_brew', 'latte', 'cappuccino', 'americano', 'filter', 'other'
);
CREATE TYPE interaction_type AS ENUM (
  'view', 'click', 'add_to_favorites', 'purchase', 'other'
);
CREATE TYPE currency AS ENUM (
  'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CHF', 'SEK', 'NOK', 'DKK', 'other'
);
CREATE TYPE roast_level AS ENUM (
  'light', 'medium_light', 'medium', 'medium_dark', 'dark', 'extra_dark', 'no_preference'
);
CREATE TYPE grind_type AS ENUM (
  'whole', 'extra_coarse', 'coarse', 'medium_coarse', 'medium', 'medium_fine', 'fine', 'extra_fine', 'turkish'
);
CREATE TYPE brewing_method AS ENUM (
  'drip_filter', 'espresso', 'pour_over', 'french_press', 'cold_brew', 'aeropress', 'moka_pot', 'siphon', 'other'
);
CREATE TYPE consumption_frequency AS ENUM (
  'daily', 'several_times_a_week', 'once_a_week', 'less_than_once_a_week'
);
CREATE TYPE flavor_or_caffeine_pref AS ENUM (
  'flavor', 'caffeine', 'either'
);
CREATE TYPE flavor_note AS ENUM (
  'chocolate_nutty', 'fruity_bright', 'caramel_sweet', 'earthy_spicy'
);
CREATE TYPE bean_type AS ENUM (
  'arabica', 'robusta', 'liberica', 'excelsa'
);
CREATE TYPE budget_range AS ENUM (
  'low', 'medium', 'high'
);

-- 2️⃣ Cafés & Locations
-- "cafes" now holds the brand‐level info; "cafe_locations" holds each physical spot.
CREATE TABLE cafes (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  description TEXT,
  website     TEXT,
  url         TEXT,
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

-- 3️⃣ Beans (updated with weight as string, price with currency, removed region_country, added url)
CREATE TABLE beans (
  id                    SERIAL PRIMARY KEY,
  name                  TEXT NOT NULL,
  weight                TEXT,
  price                 REAL,
  currency              currency,
  proprietor            TEXT,
  region_area           TEXT,
  roast_level           roast_level,
  flavor_notes          TEXT[],        
  grind_type            grind_type,
  url                   TEXT,
  created_at            TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE bean_specialties (
  bean_id               INT PRIMARY KEY REFERENCES beans(id) ON DELETE CASCADE,
  farm                  TEXT,
  altitude_masl         INT,
  process               TEXT,
  agtron_roast_level    INT,
  suitable_brew_types   brewing_method[],
  bean_type             bean_type,
  variety               TEXT
);

-- 4️⃣ Menu Items tied to a specific location, with drink type and url
CREATE TABLE menu_items (
  id            SERIAL PRIMARY KEY,
  location_id   INT REFERENCES cafe_locations(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  description   TEXT,
  price         REAL,
  currency      currency,
  drink_type    drink_type,
  url           TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- 5️⃣ Availability mappings at the location level
CREATE TABLE cafe_location_beans (
  location_id   INT REFERENCES cafe_locations(id) ON DELETE CASCADE,
  bean_id       INT REFERENCES beans(id) ON DELETE CASCADE,
  PRIMARY KEY(location_id, bean_id)
);

-- 6️⃣ Users & Preferences (added location fields)
CREATE TABLE users (
  id              SERIAL PRIMARY KEY,
  first_name      TEXT NOT NULL,
  last_name       TEXT NOT NULL,
  username        TEXT NOT NULL UNIQUE,
  email           TEXT NOT NULL UNIQUE,
  dob             DATE,
  country         TEXT,
  state           TEXT,
  city            TEXT,
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
