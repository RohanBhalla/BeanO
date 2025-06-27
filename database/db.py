from sqlalchemy import (
    create_engine, Column, Integer, Float, Date, DateTime,
    Text, ARRAY, ForeignKey, func, JSON
)
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import relationship, declarative_base
from dotenv import load_dotenv
import os

# Replace with your Supabase DATABASE_URL
try:
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
except Exception as e:
    print(f"Error loading Database URL from .env file: {e}")
    raise

Base = declarative_base()

# ENUM definitions
brewing_method = PG_ENUM(
    'drip_filter', 'espresso', 'pour_over', 'french_press', 'cold_brew', 'aeropress', 'moka_pot', 'siphon', 'other',
    name='brewing_method', create_type=True
)
roast_level = PG_ENUM(
    'light', 'medium_light', 'medium', 'medium_dark', 'dark', 'extra_dark', 'no_preference',
    name='roast_level', create_type=True
)
consumption_frequency = PG_ENUM(
    'daily', 'several_times_a_week', 'once_a_week', 'less_than_once_a_week',
    name='consumption_frequency', create_type=True
)
flavor_or_caffeine_pref = PG_ENUM(
    'flavor', 'caffeine', 'either',
    name='flavor_or_caffeine_pref', create_type=True
)
flavor_note = PG_ENUM(
    'chocolate_nutty', 'fruity_bright', 'caramel_sweet', 'earthy_spicy',
    name='flavor_note', create_type=True
)
grind_type = PG_ENUM(
    'whole', 'extra_coarse', 'coarse', 'medium_coarse', 'medium', 'medium_fine', 'fine', 'extra_fine', 'turkish',
    name='grind_type', create_type=True
)
bean_type = PG_ENUM('arabica', 'robusta', 'liberica', 'excelsa', name='bean_type', create_type=True)
budget_range = PG_ENUM('low', 'medium', 'high', name='budget_range', create_type=True)
drink_type = PG_ENUM(
    'espresso', 'cold_brew', 'latte', 'cappuccino', 'americano', 'filter', 'other',
    name='drink_type', create_type=True
)
interaction_type = PG_ENUM(
    'view', 'click', 'add_to_favorites', 'purchase', 'other',
    name='interaction_type', create_type=True
)
currency = PG_ENUM(
    'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CHF', 'SEK', 'NOK', 'DKK', 'other',
    name='currency', create_type=True
)

# Models
class User(Base):
    __tablename__ = 'users'
    id            = Column(Integer, primary_key=True)
    first_name    = Column(Text, nullable=False)
    last_name     = Column(Text, nullable=False)
    username      = Column(Text, unique=True, nullable=False)
    email         = Column(Text, unique=True, nullable=False)
    dob           = Column(Date)
    country       = Column(Text)
    state         = Column(Text)
    city          = Column(Text)
    budget_range  = Column(budget_range)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    preferences   = relationship('UserPreferences', back_populates='user', uselist=False)
    flavor_prefs  = relationship('UserFlavorPreference', back_populates='user')
    liked_beans   = relationship('UserLikedBean', back_populates='user')
    liked_locations = relationship('UserLikedLocation', back_populates='user')
    interactions  = relationship('UserInteraction', back_populates='user')

class UserPreferences(Base):
    __tablename__ = 'user_preferences'
    user_id                 = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    brewing_method          = Column(brewing_method)
    roast_level_pref        = Column(roast_level)
    consumption_frequency   = Column(consumption_frequency)
    flavor_or_caffeine_pref = Column(flavor_or_caffeine_pref)

    user = relationship('User', back_populates='preferences')

class UserFlavorPreference(Base):
    __tablename__ = 'user_flavor_preferences'
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    flavor  = Column(flavor_note, primary_key=True)

    user = relationship('User', back_populates='flavor_prefs')

class Bean(Base):
    __tablename__ = 'beans'
    id               = Column(Integer, primary_key=True)
    name             = Column(Text, nullable=False)
    description      = Column(Text)
    weight           = Column(Text)
    price            = Column(Float)
    currency         = Column(currency)
    proprietor       = Column(Text)
    region_area      = Column(Text)
    roast_level      = Column(roast_level)
    flavor_notes     = Column(ARRAY(Text))
    grind_type        = Column(grind_type)
    url              = Column(Text)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    specialties      = relationship('BeanSpecialty', back_populates='bean', uselist=False)
    locations        = relationship('CafeLocation', secondary='cafe_location_beans', back_populates='beans')
    liked_by         = relationship('UserLikedBean', back_populates='bean')

class BeanSpecialty(Base):
    __tablename__ = 'bean_specialties'
    bean_id            = Column(Integer, ForeignKey('beans.id', ondelete='CASCADE'), primary_key=True)
    farm               = Column(Text)
    altitude_masl      = Column(Integer)
    process            = Column(Text)
    agtron_roast_level = Column(Integer)
    suitable_brew_types= Column(ARRAY(brewing_method))
    bean_type          = Column(bean_type)
    variety            = Column(Text)

    bean = relationship('Bean', back_populates='specialties')

class Cafe(Base):
    __tablename__ = 'cafes'
    id          = Column(Integer, primary_key=True)
    name        = Column(Text, nullable=False)
    description = Column(Text)
    url         = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    locations   = relationship('CafeLocation', back_populates='cafe')

class CafeLocation(Base):
    __tablename__ = 'cafe_locations'
    id          = Column(Integer, primary_key=True)
    cafe_id     = Column(Integer, ForeignKey('cafes.id', ondelete='CASCADE'))
    address     = Column(Text, nullable=False)
    city        = Column(Text)
    state       = Column(Text)
    country     = Column(Text)
    postal_code = Column(Text)
    lat         = Column(Float)
    lon         = Column(Float)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    cafe        = relationship('Cafe', back_populates='locations')
    menu_items  = relationship('MenuItem', back_populates='location')
    beans       = relationship('Bean', secondary='cafe_location_beans', back_populates='locations')

class MenuItem(Base):
    __tablename__ = 'menu_items'
    id          = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey('cafe_locations.id', ondelete='CASCADE'))
    name        = Column(Text, nullable=False)
    description = Column(Text)
    price       = Column(Float)
    currency    = Column(currency)
    drink_type  = Column(drink_type)
    url         = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    location    = relationship('CafeLocation', back_populates='menu_items')

class CafeLocationBean(Base):
    __tablename__ = 'cafe_location_beans'
    location_id = Column(Integer, ForeignKey('cafe_locations.id', ondelete='CASCADE'), primary_key=True)
    bean_id     = Column(Integer, ForeignKey('beans.id', ondelete='CASCADE'), primary_key=True)

class UserLikedBean(Base):
    __tablename__ = 'user_liked_beans'
    user_id  = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    bean_id  = Column(Integer, ForeignKey('beans.id', ondelete='CASCADE'), primary_key=True)
    liked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User', back_populates='liked_beans')
    bean = relationship('Bean', back_populates='liked_by')

class UserLikedLocation(Base):
    __tablename__ = 'user_liked_locations'
    user_id     = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    location_id = Column(Integer, ForeignKey('cafe_locations.id', ondelete='CASCADE'), primary_key=True)
    liked_at    = Column(DateTime(timezone=True), server_default=func.now())

    user     = relationship('User', back_populates='liked_locations')
    location = relationship('CafeLocation')

class UserInteraction(Base):
    __tablename__ = 'user_interactions'
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    interaction  = Column(interaction_type, nullable=False)
    object_type  = Column(Text, nullable=False)
    object_id    = Column(Integer, nullable=False)
    additional_context   = Column(JSON)
    occurred_at  = Column(DateTime(timezone=True), server_default=func.now())

    user         = relationship('User', back_populates='interactions')

# Engine & initialization
def init_db():
    engine = create_engine(DATABASE_URL, echo=True)
    # create all ENUM types
    for enum in [brewing_method, roast_level, consumption_frequency,
                 flavor_or_caffeine_pref, flavor_note, grind_type,
                 bean_type, budget_range, drink_type, interaction_type, currency]:
        enum.create(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ Database schema created!")
