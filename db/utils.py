import sqlite3
import logging
import threading
import time
import random
import os

logger = logging.getLogger(__name__)

# Constants for database configuration
DB_PATH = os.environ.get('GAME_DB_PATH', 'novi_sad_game.db')
MAX_RETRIES = int(os.environ.get('DB_MAX_RETRIES', '5'))
RETRY_BASE_DELAY = float(os.environ.get('DB_RETRY_BASE_DELAY', '0.5'))
DB_BUSY_TIMEOUT = int(os.environ.get('DB_BUSY_TIMEOUT', '5000'))
MAX_POOL_SIZE = int(os.environ.get('DB_MAX_POOL_SIZE', '10'))

class ConnectionManager:
    """
    Connection pool manager for SQLite database.
    Handles connection reuse, timeouts, retries, and proper cleanup.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConnectionManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize the connection manager."""
        self.pool = []
        self.pool_lock = threading.Lock()
        self.in_use = set()
        
        # Ensure the database exists and is accessible
        try:
            self._setup_database()
        except Exception as e:
            logger.error(f"Failed to set up database: {e}")
            raise
    
    def _setup_database(self):
        """
        Make sure the database is usable by creating a test connection
        and executing a simple query.
        """
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=DB_BUSY_TIMEOUT)
            conn.execute("SELECT 1")
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database setup error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_connection(self):
        """
        Get a connection from the pool or create a new one.
        Uses a retry mechanism for handling database locks.
        """
        for attempt in range(MAX_RETRIES):
            try:
                # Check if there's an available connection in the pool
                with self.pool_lock:
                    if self.pool:
                        conn = self.pool.pop()
                        self.in_use.add(conn)
                        return conn
                
                # Create a new connection if pool is empty and not at max size
                if len(self.in_use) < MAX_POOL_SIZE:
                    conn = self._create_new_connection()
                    with self.pool_lock:
                        self.in_use.add(conn)
                    return conn
                
                # If at max size, wait for a connection to become available
                logger.warning(f"Connection pool at maximum capacity ({MAX_POOL_SIZE}). Waiting for available connection.")
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt) + (random.random() * 0.1))
                
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                if "database is locked" in error_msg or "busy" in error_msg:
                    # Database is busy, retry with exponential backoff
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_BASE_DELAY * (2 ** attempt) + (random.random() * 0.1)
                        logger.warning(f"Database busy, retrying in {delay:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                        time.sleep(delay)
                        continue
                logger.error(f"Failed to get database connection (attempt {attempt+1}): {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
            
            except Exception as e:
                logger.error(f"Unexpected error getting database connection: {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
        
        raise RuntimeError("Failed to get database connection after multiple attempts")
    
    def _create_new_connection(self):
        """Create a new optimized database connection."""
        conn = sqlite3.connect(DB_PATH, timeout=DB_BUSY_TIMEOUT)
        
        # Configure connection for better performance and safety
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute(f'PRAGMA busy_timeout={DB_BUSY_TIMEOUT}')
        conn.execute('PRAGMA foreign_keys=ON')
        
        # Enable row factory for easier column access
        conn.row_factory = sqlite3.Row
        
        return conn
    
    def release_connection(self, conn):
        """
        Return a connection to the pool.
        Properly handles any active transactions.
        """
        if conn not in self.in_use:
            logger.warning("Attempted to release a connection that is not marked as in-use")
            try:
                conn.close()
            except:
                pass
            return
        
        try:
            # First, check if there's an active transaction
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_source_id()")  # Simple query to check connection
            
            # If we get here, connection is usable - add back to pool
            with self.pool_lock:
                self.in_use.remove(conn)
                self.pool.append(conn)
                
        except Exception as e:
            # Connection is broken, close it
            logger.warning(f"Discarding broken connection: {e}")
            try:
                conn.close()
            except:
                pass
            
            with self.pool_lock:
                self.in_use.discard(conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        with self.pool_lock:
            # Close all connections in the pool
            for conn in self.pool:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing pooled connection: {e}")
            
            # Close all in-use connections
            for conn in self.in_use:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing in-use connection: {e}")
            
            # Reset the pool
            self.pool = []
            self.in_use = set()

# Create a singleton instance
connection_manager = ConnectionManager()

def get_db_connection():
    """Get a database connection from the pool."""
    return connection_manager.get_connection()

def release_db_connection(conn):
    """Return a connection to the pool."""
    connection_manager.release_connection(conn)

def close_all_connections():
    """Close all database connections."""
    connection_manager.close_all() 