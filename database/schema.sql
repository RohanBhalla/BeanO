-- enums
CREATE TYPE brewing_method AS ENUM (
  'drip_filter', 'espresso', 'pour_over', 'french_press', 'cold_brew', 'other'
);
CREATE TYPE roast_level AS ENUM (
  'light', 'medium', 'dark', 'no_preference'
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
CREATE TYPE grind_type AS ENUM ('whole', 'ground');
CREATE TYPE bean_process AS ENUM ('natural', 'washed', 'honey', 'other');
CREATE TYPE bean_type AS ENUM ('arabica', 'robusta', 'liberica', 'excelsa');
CREATE TYPE budget_range AS ENUM ('low', 'medium', 'high');

-- users & preferences
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

-- beans
CREATE TABLE beans (
  id                    SERIAL PRIMARY KEY,
  name                  TEXT NOT NULL,
  weight_g              REAL,          -- in grams
  price_usd             REAL,
  proprietor            TEXT,
  region_country        TEXT,
  region_area           TEXT,
  roast_level           roast_level,
  flavor_notes          TEXT[],        -- free-text; or you could use flavor_note[]
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

-- cafés, menu, and bean availability
CREATE TABLE cafes (
  id            SERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  website       TEXT,
  country       TEXT,
  state         TEXT,
  city          TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE menu_items (
  id            SERIAL PRIMARY KEY,
  cafe_id       INT REFERENCES cafes(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  description   TEXT,
  price_usd     REAL,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cafe_beans (
  cafe_id  INT REFERENCES cafes(id)    ON DELETE CASCADE,
  bean_id  INT REFERENCES beans(id)    ON DELETE CASCADE,
  PRIMARY KEY(cafe_id, bean_id)
);

-- user likes
CREATE TABLE user_liked_beans (
  user_id   INT REFERENCES users(id)   ON DELETE CASCADE,
  bean_id   INT REFERENCES beans(id)   ON DELETE CASCADE,
  liked_at  TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, bean_id)
);

CREATE TABLE user_liked_cafes (
  user_id   INT REFERENCES users(id)   ON DELETE CASCADE,
  cafe_id   INT REFERENCES cafes(id)   ON DELETE CASCADE,
  liked_at  TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, cafe_id)
);

