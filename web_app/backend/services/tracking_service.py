"""
Product Tracking Service
Handles all business logic for tracking products and generating alerts
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import sys
import os

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
parent_dir = os.path.dirname(os.path.dirname(backend_dir))
sys.path.insert(0, os.path.join(parent_dir, 'src'))
sys.path.insert(0, parent_dir)
sys.path.insert(0, backend_dir)

from models.database import (
    TrackedProduct, 
    ProductHistory, 
    ProductAlert, 
    get_session
)

# Import email service for sending alerts
try:
    from services.email_service import send_product_alert
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False
    def send_product_alert(*args, **kwargs):
        return False

logger = logging.getLogger(__name__)


class TrackingService:
    """Service for managing product tracking"""
    
    def __init__(self, scraper=None):
        """
        Initialize tracking service
        
        Args:
            scraper: AmazonScraper instance for fetching product data
        """
        self.scraper = scraper
    
    def add_product(
        self, 
        asin: str, 
        product_data: Dict[str, Any],
        marketplace: str = 'US',
        user_email: Optional[str] = None,
        alert_settings: Optional[Dict] = None
    ) -> TrackedProduct:
        """
        Add a product to tracking
        
        Args:
            asin: Amazon product ASIN
            product_data: Product details from search/scrape
            marketplace: Amazon marketplace (US, UK, DE)
            user_email: Optional email for alerts
            alert_settings: Optional custom alert thresholds
            
        Returns:
            TrackedProduct instance
        """
        session = get_session()
        
        try:
            # Check if already tracking
            existing = session.query(TrackedProduct).filter_by(asin=asin).first()
            if existing:
                # Reactivate if inactive
                if not existing.is_active:
                    existing.is_active = True
                    existing.last_checked = datetime.utcnow()
                    session.commit()
                return existing
            
            # Create new tracked product
            tracked = TrackedProduct(
                asin=asin,
                title=product_data.get('title', ''),
                image_url=product_data.get('image_url', ''),
                current_price=product_data.get('price'),
                current_bsr=product_data.get('bsr'),
                current_reviews=product_data.get('reviews'),
                current_rating=product_data.get('rating'),
                initial_price=product_data.get('price'),
                initial_bsr=product_data.get('bsr'),
                initial_reviews=product_data.get('reviews'),
                marketplace=marketplace,
                user_email=user_email
            )
            
            # Apply custom alert settings if provided
            if alert_settings:
                if 'price_drop_pct' in alert_settings:
                    tracked.alert_on_price_drop_pct = alert_settings['price_drop_pct']
                if 'bsr_improve_pct' in alert_settings:
                    tracked.alert_on_bsr_improve_pct = alert_settings['bsr_improve_pct']
                if 'review_increase' in alert_settings:
                    tracked.alert_on_review_increase = alert_settings['review_increase']
            
            session.add(tracked)
            session.commit()
            
            # Record initial history point
            self._record_history(session, tracked)
            
            logger.info(f"Started tracking product: {asin}")
            return tracked
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add product {asin} to tracking: {e}")
            raise
        finally:
            session.close()
    
    def remove_product(self, asin: str, hard_delete: bool = False) -> bool:
        """
        Remove a product from tracking
        
        Args:
            asin: Product ASIN
            hard_delete: If True, permanently delete. If False, just deactivate.
            
        Returns:
            True if successful
        """
        session = get_session()
        
        try:
            product = session.query(TrackedProduct).filter_by(asin=asin).first()
            if not product:
                return False
            
            if hard_delete:
                session.delete(product)
            else:
                product.is_active = False
            
            session.commit()
            logger.info(f"Removed product from tracking: {asin}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to remove product {asin}: {e}")
            raise
        finally:
            session.close()
    
    def get_tracked_products(self, active_only: bool = True) -> List[Dict]:
        """
        Get all tracked products
        
        Args:
            active_only: Only return active products
            
        Returns:
            List of product dictionaries
        """
        session = get_session()
        
        try:
            query = session.query(TrackedProduct)
            if active_only:
                query = query.filter_by(is_active=True)
            
            products = query.order_by(TrackedProduct.created_at.desc()).all()
            return [p.to_dict() for p in products]
            
        finally:
            session.close()
    
    def get_product_history(
        self, 
        asin: str, 
        days: int = 30
    ) -> List[Dict]:
        """
        Get historical data for a tracked product
        
        Args:
            asin: Product ASIN
            days: Number of days of history to return
            
        Returns:
            List of history point dictionaries
        """
        session = get_session()
        
        try:
            product = session.query(TrackedProduct).filter_by(asin=asin).first()
            if not product:
                return []
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            history = session.query(ProductHistory).filter(
                ProductHistory.product_id == product.id,
                ProductHistory.recorded_at >= cutoff
            ).order_by(ProductHistory.recorded_at.asc()).all()
            
            return [h.to_dict() for h in history]
            
        finally:
            session.close()
    
    def get_alerts(
        self, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get alerts for tracked products
        
        Args:
            unread_only: Only return unread alerts
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert dictionaries with product info
        """
        session = get_session()
        
        try:
            query = session.query(ProductAlert).join(TrackedProduct)
            if unread_only:
                query = query.filter(ProductAlert.is_read == False)
            
            alerts = query.order_by(
                ProductAlert.created_at.desc()
            ).limit(limit).all()
            
            result = []
            for alert in alerts:
                alert_dict = alert.to_dict()
                alert_dict['product'] = {
                    'asin': alert.product.asin,
                    'title': alert.product.title
                }
                result.append(alert_dict)
            
            return result
            
        finally:
            session.close()
    
    def mark_alerts_read(self, alert_ids: List[int]) -> int:
        """
        Mark alerts as read
        
        Args:
            alert_ids: List of alert IDs to mark as read
            
        Returns:
            Number of alerts updated
        """
        session = get_session()
        
        try:
            count = session.query(ProductAlert).filter(
                ProductAlert.id.in_(alert_ids)
            ).update({ProductAlert.is_read: True}, synchronize_session=False)
            
            session.commit()
            return count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to mark alerts as read: {e}")
            raise
        finally:
            session.close()
    
    def check_products(self) -> Dict[str, Any]:
        """
        Check all active tracked products for updates
        This should be called periodically (e.g., daily)
        
        Returns:
            Summary of check results
        """
        if not self.scraper:
            raise ValueError("Scraper not configured for tracking service")
        
        session = get_session()
        results = {
            'checked': 0,
            'updated': 0,
            'alerts_generated': 0,
            'errors': 0
        }
        
        try:
            products = session.query(TrackedProduct).filter_by(is_active=True).all()
            
            for product in products:
                try:
                    # Fetch current data
                    current_data = self.scraper.get_product_details(product.asin)
                    if not current_data:
                        continue
                    
                    results['checked'] += 1
                    
                    # Store previous values for comparison
                    prev_price = product.current_price
                    prev_bsr = product.current_bsr
                    prev_reviews = product.current_reviews
                    
                    # Update current values
                    new_price = current_data.get('price')
                    new_bsr = current_data.get('bsr')
                    new_reviews = current_data.get('reviews')
                    new_rating = current_data.get('rating')
                    
                    if new_price:
                        product.current_price = new_price
                    if new_bsr:
                        product.current_bsr = new_bsr
                    if new_reviews:
                        product.current_reviews = new_reviews
                    if new_rating:
                        product.current_rating = new_rating
                    
                    product.last_checked = datetime.utcnow()
                    product.check_count += 1
                    
                    # Record history
                    self._record_history(session, product)
                    results['updated'] += 1
                    
                    # Check for alerts
                    alerts = self._check_alerts(
                        session, product, 
                        prev_price, prev_bsr, prev_reviews
                    )
                    results['alerts_generated'] += len(alerts)
                    
                except Exception as e:
                    logger.error(f"Error checking product {product.asin}: {e}")
                    results['errors'] += 1
            
            session.commit()
            logger.info(f"Product check complete: {results}")
            return results
            
        except Exception as e:
            session.rollback()
            logger.error(f"Product check failed: {e}")
            raise
        finally:
            session.close()
    
    def _record_history(self, session, product: TrackedProduct):
        """Record a history point for a product"""
        history = ProductHistory(
            product_id=product.id,
            price=product.current_price,
            bsr=product.current_bsr,
            reviews=product.current_reviews,
            rating=product.current_rating
        )
        session.add(history)
    
    def _check_alerts(
        self, 
        session, 
        product: TrackedProduct,
        prev_price: float,
        prev_bsr: int,
        prev_reviews: int
    ) -> List[ProductAlert]:
        """Check if any alert thresholds are met and optionally send email"""
        alerts = []
        
        # Price drop alert
        if prev_price and product.current_price:
            price_change_pct = ((prev_price - product.current_price) / prev_price) * 100
            if price_change_pct >= product.alert_on_price_drop_pct:
                alert = ProductAlert(
                    product_id=product.id,
                    alert_type='price_drop',
                    message=f"Price dropped {price_change_pct:.1f}% from ${prev_price:.2f} to ${product.current_price:.2f}",
                    old_value=prev_price,
                    new_value=product.current_price,
                    change_pct=price_change_pct
                )
                session.add(alert)
                alerts.append(alert)
                logger.info(f"Alert: Price drop for {product.asin}")
                
                # Send email if user has email configured
                if product.user_email:
                    self._send_email_alert(product, alert)
        
        # BSR improvement alert (lower BSR is better)
        if prev_bsr and product.current_bsr:
            bsr_change_pct = ((prev_bsr - product.current_bsr) / prev_bsr) * 100
            if bsr_change_pct >= product.alert_on_bsr_improve_pct:
                alert = ProductAlert(
                    product_id=product.id,
                    alert_type='bsr_improve',
                    message=f"BSR improved {bsr_change_pct:.1f}% from #{prev_bsr:,} to #{product.current_bsr:,}",
                    old_value=prev_bsr,
                    new_value=product.current_bsr,
                    change_pct=bsr_change_pct
                )
                session.add(alert)
                alerts.append(alert)
                logger.info(f"Alert: BSR improvement for {product.asin}")
                
                # Send email if user has email configured
                if product.user_email:
                    self._send_email_alert(product, alert)
        
        # Review increase alert
        if prev_reviews and product.current_reviews:
            review_increase = product.current_reviews - prev_reviews
            if review_increase >= product.alert_on_review_increase:
                alert = ProductAlert(
                    product_id=product.id,
                    alert_type='review_increase',
                    message=f"Reviews increased by {review_increase} from {prev_reviews:,} to {product.current_reviews:,}",
                    old_value=prev_reviews,
                    new_value=product.current_reviews,
                    change_pct=(review_increase / prev_reviews) * 100 if prev_reviews else 0
                )
                session.add(alert)
                alerts.append(alert)
                logger.info(f"Alert: Review increase for {product.asin}")
                
                # Send email if user has email configured
                if product.user_email:
                    self._send_email_alert(product, alert)
        
        return alerts
    
    def _send_email_alert(self, product: TrackedProduct, alert: ProductAlert):
        """Send email notification for an alert"""
        try:
            sent = send_product_alert(
                to_email=product.user_email,
                product_title=product.title,
                asin=product.asin,
                alert_type=alert.alert_type,
                alert_message=alert.message,
                old_value=alert.old_value,
                new_value=alert.new_value
            )
            if sent:
                alert.is_emailed = True
                logger.info(f"Email alert sent to {product.user_email} for {product.asin}")
            else:
                logger.warning(f"Failed to send email alert to {product.user_email}")
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
    
    def update_alert_settings(
        self, 
        asin: str, 
        settings: Dict[str, Any]
    ) -> bool:
        """
        Update alert settings for a tracked product
        
        Args:
            asin: Product ASIN
            settings: New alert settings
            
        Returns:
            True if successful
        """
        session = get_session()
        
        try:
            product = session.query(TrackedProduct).filter_by(asin=asin).first()
            if not product:
                return False
            
            if 'price_drop_pct' in settings:
                product.alert_on_price_drop_pct = settings['price_drop_pct']
            if 'bsr_improve_pct' in settings:
                product.alert_on_bsr_improve_pct = settings['bsr_improve_pct']
            if 'review_increase' in settings:
                product.alert_on_review_increase = settings['review_increase']
            if 'user_email' in settings:
                product.user_email = settings['user_email']
            if 'notes' in settings:
                product.notes = settings['notes']
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update alert settings for {asin}: {e}")
            raise
        finally:
            session.close()
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """Get overall tracking statistics"""
        session = get_session()
        
        try:
            total = session.query(TrackedProduct).count()
            active = session.query(TrackedProduct).filter_by(is_active=True).count()
            unread_alerts = session.query(ProductAlert).filter_by(is_read=False).count()
            
            return {
                'total_products': total,
                'active_products': active,
                'unread_alerts': unread_alerts
            }
            
        finally:
            session.close()
