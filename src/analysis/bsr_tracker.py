"""
BSR History Tracker Module
Build your own historical BSR database for free!
Tracks products over time to build trend data.
"""

import logging
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)


@dataclass
class BSRSnapshot:
    asin: str
    bsr: int
    price: float
    timestamp: datetime
    category: str = None


@dataclass
class BSRTrend:
    asin: str
    current_bsr: int
    avg_bsr_7d: float
    avg_bsr_30d: float
    avg_bsr_90d: float
    bsr_variance: float  # Lower = more stable
    trend_direction: str  # 'improving', 'declining', 'stable'
    is_seasonal: bool
    data_points: int
    price_history: List[Dict]
    
    
class BSRTracker:
    """
    Free BSR tracking system - build your own historical data!
    
    Usage:
        tracker = BSRTracker()
        
        # Add snapshots (call daily via cron job or scheduled task)
        tracker.add_snapshot('B08XYZ123', bsr=5000, price=29.99)
        
        # After 30+ days, get trend data
        trend = tracker.get_trend('B08XYZ123')
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize BSR tracker with SQLite database.
        
        Args:
            db_path: Path to SQLite database file. Default: ./data/bsr_history.db
        """
        if db_path is None:
            # Store in project data folder
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'bsr_history.db')
        
        self.db_path = db_path
        self._init_db()
        
        logger.info(f"BSRTracker initialized with database: {db_path}")
    
    def _init_db(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # BSR snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bsr_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                bsr INTEGER,
                price REAL,
                category TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asin, timestamp)
            )
        ''')
        
        # Index for fast queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_asin_timestamp 
            ON bsr_snapshots(asin, timestamp)
        ''')
        
        # Product metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                asin TEXT PRIMARY KEY,
                title TEXT,
                brand TEXT,
                category TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_snapshot(self, asin: str, bsr: int, price: float = None, 
                     category: str = None, title: str = None, brand: str = None) -> bool:
        """
        Add a BSR snapshot for a product.
        Call this daily to build historical data.
        
        Args:
            asin: Product ASIN
            bsr: Current Best Sellers Rank
            price: Current price (optional)
            category: Product category (optional)
            title: Product title (optional, for metadata)
            brand: Brand name (optional, for metadata)
            
        Returns:
            True if snapshot added successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Add snapshot
            cursor.execute('''
                INSERT OR REPLACE INTO bsr_snapshots (asin, bsr, price, category, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (asin, bsr, price, category, datetime.now().isoformat()))
            
            # Update product metadata
            if title or brand:
                cursor.execute('''
                    INSERT OR REPLACE INTO products (asin, title, brand, category, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                ''', (asin, title, brand, category, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Added snapshot for {asin}: BSR={bsr}, Price={price}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding snapshot for {asin}: {str(e)}")
            return False
    
    def add_bulk_snapshots(self, snapshots: List[Dict]) -> int:
        """
        Add multiple snapshots at once (more efficient).
        
        Args:
            snapshots: List of dicts with keys: asin, bsr, price, category
            
        Returns:
            Number of snapshots added successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            data = [(s['asin'], s.get('bsr'), s.get('price'), 
                    s.get('category'), timestamp) for s in snapshots]
            
            cursor.executemany('''
                INSERT OR REPLACE INTO bsr_snapshots (asin, bsr, price, category, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', data)
            
            count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Added {count} bulk snapshots")
            return count
            
        except Exception as e:
            logger.error(f"Error adding bulk snapshots: {str(e)}")
            return 0
    
    def get_trend(self, asin: str) -> Optional[BSRTrend]:
        """
        Get BSR trend analysis for a product.
        Requires at least 7 days of data for meaningful results.
        
        Args:
            asin: Product ASIN
            
        Returns:
            BSRTrend object or None if insufficient data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all snapshots for this ASIN
            cursor.execute('''
                SELECT bsr, price, timestamp FROM bsr_snapshots
                WHERE asin = ?
                ORDER BY timestamp DESC
            ''', (asin,))
            
            rows = cursor.fetchall()
            conn.close()
            
            if len(rows) < 3:
                logger.warning(f"Insufficient data for {asin}: only {len(rows)} snapshots")
                return None
            
            # Parse data
            now = datetime.now()
            bsr_7d = []
            bsr_30d = []
            bsr_90d = []
            all_bsr = []
            price_history = []
            
            for bsr, price, timestamp in rows:
                if bsr is None:
                    continue
                    
                ts = datetime.fromisoformat(timestamp)
                age_days = (now - ts).days
                
                all_bsr.append(bsr)
                price_history.append({'price': price, 'date': timestamp})
                
                if age_days <= 7:
                    bsr_7d.append(bsr)
                if age_days <= 30:
                    bsr_30d.append(bsr)
                if age_days <= 90:
                    bsr_90d.append(bsr)
            
            if not all_bsr:
                return None
            
            # Calculate metrics
            current_bsr = all_bsr[0]  # Most recent
            avg_7d = statistics.mean(bsr_7d) if bsr_7d else current_bsr
            avg_30d = statistics.mean(bsr_30d) if bsr_30d else current_bsr
            avg_90d = statistics.mean(bsr_90d) if bsr_90d else current_bsr
            
            # Variance (lower = more stable)
            variance = statistics.stdev(bsr_30d) / avg_30d if len(bsr_30d) > 1 and avg_30d > 0 else 0
            
            # Trend direction
            if len(bsr_7d) >= 2:
                recent_avg = statistics.mean(bsr_7d[:len(bsr_7d)//2])
                older_avg = statistics.mean(bsr_7d[len(bsr_7d)//2:])
                
                if recent_avg < older_avg * 0.9:
                    trend = 'improving'  # BSR getting lower = better
                elif recent_avg > older_avg * 1.1:
                    trend = 'declining'  # BSR getting higher = worse
                else:
                    trend = 'stable'
            else:
                trend = 'unknown'
            
            # Seasonality detection (high variance)
            is_seasonal = variance > 0.5  # 50% variance suggests seasonality
            
            return BSRTrend(
                asin=asin,
                current_bsr=current_bsr,
                avg_bsr_7d=round(avg_7d, 0),
                avg_bsr_30d=round(avg_30d, 0),
                avg_bsr_90d=round(avg_90d, 0),
                bsr_variance=round(variance, 3),
                trend_direction=trend,
                is_seasonal=is_seasonal,
                data_points=len(all_bsr),
                price_history=price_history[:30]  # Last 30 price points
            )
            
        except Exception as e:
            logger.error(f"Error getting trend for {asin}: {str(e)}")
            return None
    
    def get_stability_score(self, asin: str) -> float:
        """
        Get a simple stability score (0-10) based on BSR variance.
        Higher = more stable = better.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Stability score (0-10) or -1 if insufficient data
        """
        trend = self.get_trend(asin)
        if not trend:
            return -1
        
        # Convert variance to score (inverse relationship)
        # Variance 0 = score 10, Variance 1.0 = score 0
        score = max(0, 10 - (trend.bsr_variance * 10))
        return round(score, 1)
    
    def get_tracked_asins(self) -> List[str]:
        """Get list of all ASINs being tracked."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT DISTINCT asin FROM bsr_snapshots')
            asins = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return asins
            
        except Exception as e:
            logger.error(f"Error getting tracked ASINs: {str(e)}")
            return []
    
    def get_tracking_stats(self) -> Dict:
        """Get statistics about tracking database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(DISTINCT asin) FROM bsr_snapshots')
            total_asins = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM bsr_snapshots')
            total_snapshots = cursor.fetchone()[0]
            
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM bsr_snapshots')
            min_ts, max_ts = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_asins_tracked': total_asins,
                'total_snapshots': total_snapshots,
                'oldest_data': min_ts,
                'newest_data': max_ts,
                'database_path': self.db_path
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {}
    
    def cleanup_old_data(self, days: int = 365):
        """
        Remove data older than specified days to keep database size manageable.
        
        Args:
            days: Remove data older than this many days
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('DELETE FROM bsr_snapshots WHERE timestamp < ?', (cutoff,))
            deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted} snapshots older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
    
    def export_to_json(self, asin: str = None) -> str:
        """
        Export tracking data to JSON.
        
        Args:
            asin: Specific ASIN to export, or None for all
            
        Returns:
            JSON string of tracking data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if asin:
                cursor.execute('''
                    SELECT asin, bsr, price, category, timestamp 
                    FROM bsr_snapshots WHERE asin = ?
                    ORDER BY timestamp DESC
                ''', (asin,))
            else:
                cursor.execute('''
                    SELECT asin, bsr, price, category, timestamp 
                    FROM bsr_snapshots
                    ORDER BY asin, timestamp DESC
                ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            data = [
                {'asin': r[0], 'bsr': r[1], 'price': r[2], 
                 'category': r[3], 'timestamp': r[4]}
                for r in rows
            ]
            
            return json.dumps(data, indent=2)
            
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return "[]"
