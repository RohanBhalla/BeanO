from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime,
    Enum, Text, ARRAY, ForeignKey, func
)
from dotenv import load_dotenv
import os
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import relationship, declarative_base, sessionmaker

# — replace with your Supabase DATABASE_URL
try:
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
except Exception as e:
    print(f"Error loading Database URL from .env file: {e}")
    raise

Base = declarative_base()

# 1️⃣ ENUM definitions
brewing_method = PG_ENUM(
    'drip_filter', 'espresso', 'pour_over', 'french_press', 'cold_brew', 'other',
    name='brewing_method', create_type=False
)
roast_level = PG_ENUM(
    'light', 'medium', 'dark', 'no_preference',
    name='roast_level', create_type=False
)
consumption_frequency = PG_ENUM(
    'daily', 'several_times_a_week', 'once_a_week', 'less_than_once_a_week',
    name='consumption_frequency', create_type=False
)
flavor_or_caffeine_pref = PG_ENUM(
    'flavor', 'caffeine', 'either',
    name='flavor_or_caffeine_pref', create_type=False
)
flavor_note = PG_ENUM(
    'chocolate_nutty', 'fruity_bright', 'caramel_sweet', 'earthy_spicy',
    name='flavor_note', create_type=False
)
grind_type = PG_ENUM('whole', 'ground', name='grind_type', create_type=False)
bean_process = PG_ENUM('natural', 'washed', 'honey', 'other', name='bean_process', create_type=False)
bean_type = PG_ENUM('arabica', 'robusta', 'liberica', 'excelsa', name='bean_type', create_type=False)
budget_range = PG_ENUM('low', 'medium', 'high', name='budget_range', create_type=False)

# 2️⃣ Models
class User(Base):
    __tablename__ = 'users'
    id            = Column(Integer, primary_key=True)
    first_name    = Column(Text, nullable=False)
    last_name     = Column(Text, nullable=False)
    username      = Column(Text, unique=True, nullable=False)
    email         = Column(Text, unique=True, nullable=False)
    dob           = Column(Date)
    budget_range  = Column(budget_range)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    preferences    = relationship('UserPreferences', back_populates='user', uselist=False)
    flavor_prefs   = relationship('UserFlavorPreference', back_populates='user')
    liked_beans    = relationship('UserLikedBean', back_populates='user')
    liked_cafes    = relationship('UserLikedCafe', back_populates='user')

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
    weight_g         = Column(Float)
    price_usd        = Column(Float)
    proprietor       = Column(Text)
    region_country   = Column(Text)
    region_area      = Column(Text)
    roast_level      = Column(roast_level)
    flavor_notes     = Column(ARRAY(Text))
    grind_type       = Column(grind_type)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    specialties      = relationship('BeanSpecialty', back_populates='bean', uselist=False)
    cafes            = relationship('Cafe', secondary='cafe_beans', back_populates='beans')
    liked_by         = relationship('UserLikedBean', back_populates='bean')

class BeanSpecialty(Base):
    __tablename__ = 'bean_specialties'
    bean_id            = Column(Integer, ForeignKey('beans.id', ondelete='CASCADE'), primary_key=True)
    farm               = Column(Text)
    altitude_masl      = Column(Integer)
    process            = Column(bean_process)
    agtron_roast_level = Column(Integer)
    suitable_brew_types= Column(ARRAY(brewing_method))
    bean_type          = Column(bean_type)
    variety            = Column(Text)

    bean = relationship('Bean', back_populates='specialties')

class Cafe(Base):
    __tablename__ = 'cafes'
    id         = Column(Integer, primary_key=True)
    name       = Column(Text, nullable=False)
    website    = Column(Text)
    country    = Column(Text)
    state      = Column(Text)
    city       = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    beans       = relationship('Bean', secondary='cafe_beans', back_populates='cafes')
    menu_items  = relationship('MenuItem', back_populates='cafe')
    liked_by    = relationship('UserLikedCafe', back_populates='cafe')

class CafeBean(Base):
    __tablename__ = 'cafe_beans'
    cafe_id = Column(Integer, ForeignKey('cafes.id', ondelete='CASCADE'), primary_key=True)
    bean_id = Column(Integer, ForeignKey('beans.id', ondelete='CASCADE'), primary_key=True)

class MenuItem(Base):
    __tablename__ = 'menu_items'
    id          = Column(Integer, primary_key=True)
    cafe_id     = Column(Integer, ForeignKey('cafes.id', ondelete='CASCADE'))
    name        = Column(Text, nullable=False)
    description = Column(Text)
    price_usd   = Column(Float)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    cafe = relationship('Cafe', back_populates='menu_items')

class UserLikedBean(Base):
    __tablename__ = 'user_liked_beans'
    user_id  = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    bean_id  = Column(Integer, ForeignKey('beans.id', ondelete='CASCADE'), primary_key=True)
    liked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User', back_populates='liked_beans')
    bean = relationship('Bean', back_populates='liked_by')

class UserLikedCafe(Base):
    __tablename__ = 'user_liked_cafes'
    user_id  = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    cafe_id  = Column(Integer, ForeignKey('cafes.id', ondelete='CASCADE'), primary_key=True)
    liked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User', back_populates='liked_cafes')
    cafe = relationship('Cafe', back_populates='liked_by')

# 3️⃣ Create engine & tables
def init_db():
    engine = create_engine(DATABASE_URL, echo=True)
    # create enums in Postgres if not exist
    for enum in [brewing_method, roast_level, consumption_frequency,
                 flavor_or_caffeine_pref, flavor_note, grind_type,
                 bean_process, bean_type, budget_range]:
        enum.create(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ Database schema created!")
