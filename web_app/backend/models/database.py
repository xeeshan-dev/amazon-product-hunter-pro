"""
Database models for Product Tracking & Alerts
Uses SQLite for lightweight storage without external dependencies
"""
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'amazon_hunter.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Create engine
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class TrackedProduct(Base):
    """Products being tracked for price/BSR changes"""
    __tablename__ = 'tracked_products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(500))
    image_url = Column(String(500))
    
    # Current values (updated on each check)
    current_price = Column(Float)
    current_bsr = Column(Integer)
    current_reviews = Column(Integer)
    current_rating = Column(Float)
    
    # Initial values (when tracking started)
    initial_price = Column(Float)
    initial_bsr = Column(Integer)
    initial_reviews = Column(Integer)
    
    # Tracking metadata
    marketplace = Column(String(10), default='US')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime, default=datetime.utcnow)
    check_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Alert settings
    alert_on_price_drop_pct = Column(Float, default=5.0)  # Alert if price drops by this %
    alert_on_bsr_improve_pct = Column(Float, default=10.0)  # Alert if BSR improves by this %
    alert_on_review_increase = Column(Integer, default=50)  # Alert if reviews increase by this count
    
    # User preferences (for future multi-user support)
    user_email = Column(String(255))
    notes = Column(Text)
    
    # Relationship to history
    history = relationship("ProductHistory", back_populates="product", cascade="all, delete-orphan")
    alerts = relationship("ProductAlert", back_populates="product", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'asin': self.asin,
            'title': self.title,
            'image_url': self.image_url,
            'current_price': self.current_price,
            'current_bsr': self.current_bsr,
            'current_reviews': self.current_reviews,
            'current_rating': self.current_rating,
            'initial_price': self.initial_price,
            'initial_bsr': self.initial_bsr,
            'initial_reviews': self.initial_reviews,
            'marketplace': self.marketplace,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'check_count': self.check_count,
            'is_active': self.is_active,
            'alert_settings': {
                'price_drop_pct': self.alert_on_price_drop_pct,
                'bsr_improve_pct': self.alert_on_bsr_improve_pct,
                'review_increase': self.alert_on_review_increase
            },
            'user_email': self.user_email,
            'notes': self.notes,
            # Computed changes
            'price_change_pct': self._calculate_change(self.initial_price, self.current_price),
            'bsr_change_pct': self._calculate_change(self.initial_bsr, self.current_bsr, invert=True),
            'review_change': (self.current_reviews or 0) - (self.initial_reviews or 0)
        }
    
    def _calculate_change(self, initial, current, invert=False):
        if not initial or not current:
            return 0
        change = ((current - initial) / initial) * 100
        return -change if invert else change


class ProductHistory(Base):
    """Historical data points for tracked products"""
    __tablename__ = 'product_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('tracked_products.id'), nullable=False)
    
    # Snapshot values
    price = Column(Float)
    bsr = Column(Integer)
    reviews = Column(Integer)
    rating = Column(Float)
    
    # Metadata
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    product = relationship("TrackedProduct", back_populates="history")
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'price': self.price,
            'bsr': self.bsr,
            'reviews': self.reviews,
            'rating': self.rating,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


class ProductAlert(Base):
    """Alerts generated for tracked products"""
    __tablename__ = 'product_alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('tracked_products.id'), nullable=False)
    
    # Alert details
    alert_type = Column(String(50))  # 'price_drop', 'bsr_improve', 'review_increase'
    message = Column(Text)
    old_value = Column(Float)
    new_value = Column(Float)
    change_pct = Column(Float)
    
    # Status
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    is_emailed = Column(Boolean, default=False)
    
    # Relationship
    product = relationship("TrackedProduct", back_populates="alerts")
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'alert_type': self.alert_type,
            'message': self.message,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'change_pct': self.change_pct,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_read': self.is_read,
            'is_emailed': self.is_emailed
        }


# Create all tables
def init_db():
    """Initialize the database tables"""
    Base.metadata.create_all(engine)
    return True


def get_session():
    """Get a new database session"""
    return Session()


# Initialize on import
init_db()
