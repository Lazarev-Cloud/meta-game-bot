import sqlite3
import logging
import datetime
import json
import time
import threading
from functools import wraps
from typing import Callable, Any, Optional, Dict, Union

logger = logging.getLogger(__name__)


class DatabaseConnectionPoolError(Exception):
    """Custom exception for database connection pool errors."""
    pass


class DatabaseConnectionPool:
    """
    Thread-safe SQLite connection pool with advanced features.

    Features:
    - Configurable max connections
    - Connection timeout handling
    - Exponential backoff for retries
    - Foreign key enforcement
    - Connection validation
    """

    def __init__(
            self,
            db_path: str = 'belgrade_game.db',
            max_connections: int = 10,
            timeout: float = 10.0,
            max_retries: int = 3,
            initial_pragmas: Optional[Dict[str, str]] = None
    ):
        """Initialize database connection pool with thread-local storage."""
        self._db_path = db_path
        self._max_connections = max_connections
        self._timeout = timeout
        self._max_retries = max_retries
        self._pragmas = {
            "foreign_keys": "ON",
            "journal_mode": "WAL",
            "synchronous": "NORMAL",
            "cache_size": "-2000"
        }
        if initial_pragmas:
            self._pragmas.update(initial_pragmas)

        self._pool: list[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._connection_count = 0

        # Thread-local storage for connections
        self._local = threading.local()

        self._initialize_database()

    def _initialize_database(self):
        """
        Create initial database configuration if needed.
        Ensures database setup and initial PRAGMA configurations.
        """
        conn = None
        try:
            conn = sqlite3.connect(self._db_path, timeout=self._timeout)

            # Apply all configured PRAGMA settings
            for pragma, value in self._pragmas.items():
                try:
                    conn.execute(f"PRAGMA {pragma} = {value}")
                except sqlite3.Error as pragma_error:
                    logger.warning(f"Could not set PRAGMA {pragma}: {pragma_error}")

            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise DatabaseConnectionPoolError(f"Failed to initialize database: {e}")
        finally:
            if conn:
                conn.close()

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection with configured PRAGMAs.

        :return: Configured SQLite database connection
        """
        try:
            conn = sqlite3.connect(
                self._db_path,
                timeout=self._timeout,
                isolation_level=None  # Enable autocommit mode
            )

            # Apply all configured PRAGMA settings
            for pragma, value in self._pragmas.items():
                conn.execute(f"PRAGMA {pragma} = {value}")

            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to create database connection: {e}")
            raise DatabaseConnectionPoolError(f"Connection creation failed: {e}")

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection specific to the current thread.

        Returns:
            A SQLite connection for the current thread
        """
        # Check if there's already a connection for this thread
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                # Test the connection
                self._local.connection.execute("SELECT 1")
                return self._local.connection
            except (sqlite3.Error, sqlite3.ProgrammingError):
                # Connection is invalid, remove it
                self._local.connection = None

        # Get a new connection
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
            elif self._connection_count < self._max_connections:
                self._connection_count += 1
                conn = self._create_connection()
            else:
                raise DatabaseConnectionPoolError("No available database connections")

        # Store in thread-local storage
        self._local.connection = conn
        return conn

    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool."""
        # If it's the thread's connection, just keep it for reuse
        if hasattr(self._local, 'connection') and self._local.connection is conn:
            return

        # Otherwise return to pool as before
        with self._lock:
            try:
                conn.execute("SELECT 1")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                try:
                    conn.close()
                except Exception:
                    pass
                self._connection_count -= 1
                return

            if len(self._pool) < self._max_connections:
                self._pool.append(conn)
            else:
                try:
                    conn.close()
                except Exception:
                    pass
                self._connection_count -= 1

    def close_thread_connection(self):
        """Close and remove the current thread's connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
            except Exception:
                pass
            self._local.connection = None

    def close_all_connections(self):
        """
        Close all connections in the pool.
        """
        with self._lock:
            while self._pool:
                conn = self._pool.pop()
                try:
                    conn.close()
                except Exception:
                    pass
            self._connection_count = 0


# Global database pool instance
db_connection_pool = DatabaseConnectionPool()


def db_transaction(func: Callable) -> Callable:
    """
    Decorator for database transactions with advanced error handling.
    Uses thread-local connections.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        conn = None
        retry_delay = 0.5  # seconds
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Get thread-local connection from the pool
                conn = db_connection_pool.get_connection()

                # Start a transaction
                conn.execute("BEGIN")

                # Execute the function with the connection
                result = func(conn, *args, **kwargs)

                # Commit the transaction
                conn.commit()

                return result

            except sqlite3.OperationalError as e:
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                logger.error(f"Database operational error in {func.__name__}: {e}")
                raise

            except Exception as e:
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                raise

            finally:
                # No need to explicitly return the connection if using thread-local storage
                pass

    return wrapper


# Cleanup method to be called when the application exits
def cleanup_database_pool():
    """
    Close all database connections when application exits.
    """
    try:
        db_connection_pool.close_all_connections()
    except Exception as e:
        logger.error(f"Error during database pool cleanup: {e}")


# Optional: Context manager for manual connection management
class DatabaseConnectionPool:
    """
    Advanced thread-safe SQLite connection pool with robust error handling
    """

    def __init__(
            self,
            db_path: str = 'belgrade_game.db',
            max_connections: int = 10,
            timeout: float = 30.0,  # Increased timeout
            max_retries: int = 5,  # Increased retry attempts
            initial_pragmas: Optional[Dict[str, str]] = None
    ):
        self._db_path = db_path
        self._max_connections = max_connections
        self._timeout = timeout
        self._max_retries = max_retries

        # Enhanced PRAGMA settings for better concurrency and performance
        self._pragmas = {
            "foreign_keys": "ON",
            "journal_mode": "WAL",  # Write-Ahead Logging for better concurrency
            "synchronous": "NORMAL",
            "cache_size": "-2000",  # Larger cache
            "temp_store": "MEMORY"  # Use memory for temp tables
        }
        if initial_pragmas:
            self._pragmas.update(initial_pragmas)

        self._pool: list[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._connection_count = 0
        self._local = threading.local()

        # Set up initial database configuration
        self._initialize_database()

    def _initialize_database(self):
        """
        Create initial database configuration with enhanced settings
        """
        try:
            conn = sqlite3.connect(self._db_path, timeout=self._timeout)

            # Apply all configured PRAGMA settings
            for pragma, value in self._pragmas.items():
                try:
                    conn.execute(f"PRAGMA {pragma} = {value}")
                except sqlite3.Error as pragma_error:
                    logger.warning(f"Could not set PRAGMA {pragma}: {pragma_error}")

            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise DatabaseConnectionPoolError(f"Failed to initialize database: {e}")

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection with exponential backoff and robust error handling
        """
        retry_delay = 0.1  # Start with a small delay
        for attempt in range(self._max_retries):
            try:
                # Check thread-local connection
                if hasattr(self._local, 'connection') and self._local.connection:
                    try:
                        # Validate connection
                        self._local.connection.execute("SELECT 1")
                        return self._local.connection
                    except (sqlite3.Error, sqlite3.ProgrammingError):
                        self._local.connection = None

                # Acquire lock and get/create connection
                with self._lock:
                    if self._pool:
                        conn = self._pool.pop()
                    elif self._connection_count < self._max_connections:
                        self._connection_count += 1
                        conn = self._create_connection()
                    else:
                        raise DatabaseConnectionPoolError("No available database connections")

                # Store in thread-local storage
                self._local.connection = conn
                return conn

            except (sqlite3.OperationalError, DatabaseConnectionPoolError) as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

                # Exponential backoff with jitter
                time.sleep(retry_delay * (1 + random.random()))
                retry_delay *= 2  # Exponential increase

                if attempt == self._max_retries - 1:
                    logger.error(f"Failed to get database connection after {self._max_retries} attempts")
                    raise

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection with configured PRAGMAs
        """
        try:
            conn = sqlite3.connect(
                self._db_path,
                timeout=self._timeout,
                isolation_level=None  # Enable autocommit mode
            )

            # Apply all configured PRAGMA settings
            for pragma, value in self._pragmas.items():
                conn.execute(f"PRAGMA {pragma} = {value}")

            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to create database connection: {e}")
            raise DatabaseConnectionPoolError(f"Connection creation failed: {e}")

    def return_connection(self, conn: sqlite3.Connection):
        """
        Return a connection to the pool with validation
        """
        with self._lock:
            try:
                # Validate connection
                conn.execute("SELECT 1")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                try:
                    conn.close()
                except Exception:
                    pass
                self._connection_count -= 1
                return

            if len(self._pool) < self._max_connections:
                self._pool.append(conn)
            else:
                try:
                    conn.close()
                except Exception:
                    pass
                self._connection_count -= 1

    def close_all_connections(self):
        """
        Gracefully close all connections in the pool
        """
        with self._lock:
            while self._pool:
                conn = self._pool.pop()
                try:
                    conn.close()
                except Exception:
                    pass
            self._connection_count = 0
            if hasattr(self._local, 'connection'):
                self._local.connection = None
# Player-related queries
@db_transaction
def get_player(conn, player_id):
    """Get player information by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
    player = cursor.fetchone()
    return player


@db_transaction
def register_player(conn, player_id, username, language="en"):
    """Register a new player."""
    cursor = conn.cursor()

    # Check if player already exists
    cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
    if cursor.fetchone() is None:
        # Insert new player
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO players (player_id, username, last_action_refresh, language) VALUES (?, ?, ?, ?)",
            (player_id, username, now, language)
        )

        # Initialize resources
        cursor.execute(
            "INSERT INTO resources (player_id, influence, resources, information, force) VALUES (?, 5, 5, 5, 5)",
            (player_id,)
        )

        return True
    return False


@db_transaction
def set_player_name(conn, player_id, character_name):
    """Set player's character name."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET character_name = ? WHERE player_id = ?",
        (character_name, player_id)
    )
    return cursor.rowcount > 0


@db_transaction
def get_player_language(conn, player_id):
    """Get player's preferred language."""
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM players WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()
    return result[0] if result else "en"


@db_transaction
def set_player_language(conn, player_id, language):
    """Set player's preferred language."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET language = ? WHERE player_id = ?",
        (language, player_id)
    )
    return cursor.rowcount > 0


@db_transaction
def update_player_resources(conn, player_id, resource_type, amount):
    """Update player's resources."""
    cursor = conn.cursor()

    # Get current resource amount
    cursor.execute(f"SELECT {resource_type} FROM resources WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()

    if result is None:
        # Player doesn't exist in resources table
        logger.error(f"Player {player_id} not found in resources table")
        return 0

    current = result[0]

    # Update resource
    new_amount = current + amount
    if new_amount < 0:
        new_amount = 0

    cursor.execute(
        f"UPDATE resources SET {resource_type} = ? WHERE player_id = ?",
        (new_amount, player_id)
    )

    return new_amount


@db_transaction
def get_player_resources(conn, player_id):
    """Get player's current resources."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resources WHERE player_id = ?", (player_id,))
    resources = cursor.fetchone()

    if resources:
        return {
            "influence": resources[1],
            "resources": resources[2],
            "information": resources[3],
            "force": resources[4]
        }
    return None


# District-related queries
@db_transaction
def get_district_info(conn, district_id):
    """Get district information by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM districts WHERE district_id = ?", (district_id,))
    return cursor.fetchone()


@db_transaction
def get_all_districts(conn):
    """Get all districts."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM districts")
    return cursor.fetchall()


@db_transaction
def get_district_control(conn, district_id):
    """Get control information for a district."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT dc.player_id, dc.control_points, p.character_name 
        FROM district_control dc
        JOIN players p ON dc.player_id = p.player_id
        WHERE dc.district_id = ?
        ORDER BY dc.control_points DESC
        """,
        (district_id,)
    )
    return cursor.fetchall()


@db_transaction
def get_player_districts(conn, player_id):
    """Get districts controlled by a player."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT d.district_id, d.name, dc.control_points 
        FROM district_control dc
        JOIN districts d ON dc.district_id = d.district_id
        WHERE dc.player_id = ?
        ORDER BY dc.control_points DESC
        """,
        (player_id,)
    )
    return cursor.fetchall()


@db_transaction
def update_district_control(conn, player_id, district_id, points_change):
    """Update district control points."""
    cursor = conn.cursor()

    # Check if player already has control points in this district
    cursor.execute(
        "SELECT control_points FROM district_control WHERE player_id = ? AND district_id = ?",
        (player_id, district_id)
    )
    existing = cursor.fetchone()

    if existing:
        # Update existing control points
        new_points = max(0, existing[0] + points_change)  # Ensure points don't go below 0
        cursor.execute(
            "UPDATE district_control SET control_points = ?, last_action = ? WHERE player_id = ? AND district_id = ?",
            (new_points, datetime.datetime.now().isoformat(), player_id, district_id)
        )
    else:
        # Insert new control record
        points = max(0, points_change)  # Ensure points don't go below 0
        cursor.execute(
            "INSERT INTO district_control (district_id, player_id, control_points, last_action) VALUES (?, ?, ?, ?)",
            (district_id, player_id, points, datetime.datetime.now().isoformat())
        )
    return True


# Politician-related queries
@db_transaction
def get_politician_info(conn, politician_id=None, name=None):
    """Get politician information by ID or name."""
    cursor = conn.cursor()

    if politician_id:
        cursor.execute("SELECT * FROM politicians WHERE politician_id = ?", (politician_id,))
    elif name:
        cursor.execute("SELECT * FROM politicians WHERE name LIKE ?", (f"%{name}%",))
    else:
        return None

    return cursor.fetchone()


@db_transaction
def get_all_politicians(conn, is_international=False):
    """Get all politicians (local or international)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM politicians WHERE is_international = ? ORDER BY name",
        (1 if is_international else 0,)
    )
    return cursor.fetchall()


@db_transaction
def update_politician_friendliness(conn, politician_id, player_id, change):
    """Update the friendliness level between a player and a politician."""
    cursor = conn.cursor()

    # Check if the relationship exists, if not, create it
    cursor.execute(
        """
        INSERT OR IGNORE INTO politician_relationships 
        (politician_id, player_id, friendliness, last_interaction, interaction_count) 
        VALUES (?, ?, 50, ?, 0)
        """,
        (politician_id, player_id, datetime.datetime.now().isoformat())
    )

    # Update the relationship
    cursor.execute(
        """
        UPDATE politician_relationships
        SET 
            friendliness = MAX(0, MIN(100, friendliness + ?)),
            last_interaction = ?,
            interaction_count = interaction_count + 1
        WHERE politician_id = ? AND player_id = ?
        """,
        (change, datetime.datetime.now().isoformat(), politician_id, player_id)
    )

    # Get the updated relationship
    cursor.execute(
        """
        SELECT friendliness, interaction_count, last_interaction
        FROM politician_relationships
        WHERE politician_id = ? AND player_id = ?
        """,
        (politician_id, player_id)
    )
    relationship = cursor.fetchone()

    # Update the global politician friendliness
    cursor.execute(
        """
        UPDATE politicians
        SET friendliness = (
            SELECT AVG(friendliness) 
            FROM politician_relationships 
            WHERE politician_id = ?
        )
        WHERE politician_id = ?
        """,
        (politician_id, politician_id)
    )

    # Return detailed relationship information
    if relationship:
        friendliness, interaction_count, last_interaction = relationship
        return {
            "politician_id": politician_id,
            "player_id": player_id,
            "friendliness": friendliness,
            "interaction_count": interaction_count,
            "last_interaction": last_interaction,
            "change": change
        }
    return None


# Action-related queries
@db_transaction
def add_action(conn, player_id, action_type, target_type, target_id, resources_used):
    """Add a new action."""
    cursor = conn.cursor()

    now = datetime.datetime.now()

    # Determine current cycle
    current_time = now.time()
    if datetime.time(6, 0) <= current_time < datetime.time(13, 1):
        cycle = "morning"
    else:
        cycle = "evening"

    cursor.execute(
        """
        INSERT INTO actions (player_id, action_type, target_type, target_id, resources_used, timestamp, cycle, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (player_id, action_type, target_type, target_id, json.dumps(resources_used), now.isoformat(), cycle)
    )
    return cursor.lastrowid


@db_transaction
def cancel_last_action(conn, player_id):
    """Cancel the last pending action and refund resources."""
    cursor = conn.cursor()

    # Get the last pending action
    cursor.execute(
        """
        SELECT action_id, action_type, resources_used 
        FROM actions 
        WHERE player_id = ? AND status = 'pending' 
        ORDER BY timestamp DESC LIMIT 1
        """,
        (player_id,)
    )
    last_action = cursor.fetchone()

    if last_action:
        action_id, action_type, resources_used = last_action
        resources_used = json.loads(resources_used)

        # Delete the action
        cursor.execute("DELETE FROM actions WHERE action_id = ?", (action_id,))

        # Refund resources
        for resource_type, amount in resources_used.items():
            # Update the player's resources
            update_player_resources_internal(conn, player_id, resource_type, amount)
        return True
    return False


# Helper function for internal use within the module
def update_player_resources_internal(conn, player_id, resource_type, amount):
    """Update player resources (internal function without transaction)."""
    cursor = conn.cursor()

    # Get current resource amount
    cursor.execute(f"SELECT {resource_type} FROM resources WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()

    if not result:
        logger.error(f"Player {player_id} not found in resources table")
        return 0

    current = result[0]

    # Update resource
    new_amount = current + amount
    if new_amount < 0:
        new_amount = 0

    cursor.execute(
        f"UPDATE resources SET {resource_type} = ? WHERE player_id = ?",
        (new_amount, player_id)
    )
    return new_amount


@db_transaction
def get_remaining_actions(conn, player_id):
    """Get remaining actions for player."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT main_actions_left, quick_actions_left FROM players WHERE player_id = ?",
        (player_id,)
    )
    actions = cursor.fetchone()
    if actions:
        return {"main": actions[0], "quick": actions[1]}
    return {"main": 0, "quick": 0}


@db_transaction
def use_action(conn, player_id, is_main_action):
    """Decrement action count when player uses an action."""
    cursor = conn.cursor()
    if is_main_action:
        cursor.execute(
            "UPDATE players SET main_actions_left = main_actions_left - 1 WHERE player_id = ? AND main_actions_left > 0",
            (player_id,)
        )
    else:
        cursor.execute(
            "UPDATE players SET quick_actions_left = quick_actions_left - 1 WHERE player_id = ? AND quick_actions_left > 0",
            (player_id,)
        )
    return cursor.rowcount > 0


@db_transaction
def refresh_player_actions(conn, player_id):
    """Reset action counts and update refresh timestamp."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute(
        "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ? WHERE player_id = ?",
        (now, player_id)
    )
    return cursor.rowcount > 0



@db_transaction
def update_action_counts(conn, player_id):
    """Reset action counts if it's been more than 3 hours since last refresh."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_action_refresh FROM players WHERE player_id = ?",
        (player_id,)
    )
    last_refresh = cursor.fetchone()

    if not last_refresh:
        return False

    last_refresh_time = datetime.datetime.fromisoformat(last_refresh[0])
    now = datetime.datetime.now()

    # If it's been more than 3 hours
    if (now - last_refresh_time).total_seconds() > 3 * 60 * 60:
        cursor.execute(
            "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ? WHERE player_id = ?",
            (now.isoformat(), player_id)
        )
        return True
    return False

# News-related queries
@db_transaction
def add_news(conn, title, content, is_public=True, target_player_id=None, is_fake=False):
    """
    Add a news item with robust handling of timestamp
    """
    cursor = conn.cursor()

    # Ensure created_at column exists, if not, use current timestamp
    try:
        now = datetime.datetime.now().isoformat()

        # Try to insert with created_at
        cursor.execute(
            """
            INSERT INTO news (title, content, created_at, timestamp, is_public, target_player_id, is_fake)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, content, now, now, is_public, target_player_id, is_fake)
        )
    except sqlite3.OperationalError as e:
        # If column doesn't exist, fall back to basic insertion
        if "no such column" in str(e).lower():
            logger.warning("News table missing created_at column. Using alternative insertion.")
            cursor.execute(
                """
                INSERT INTO news (title, content, timestamp, is_public, target_player_id, is_fake)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, content, now, is_public, target_player_id, is_fake)
            )
        else:
            raise

    return cursor.lastrowid


@db_transaction
def get_news(conn, limit=5, player_id=None):
    """Get recent news items."""
    cursor = conn.cursor()
    if player_id:
        cursor.execute(
            """
            SELECT * FROM news 
            WHERE is_public = 1 OR target_player_id = ? 
            ORDER BY timestamp DESC LIMIT ?
            """,
            (player_id, limit)
        )
    else:
        cursor.execute(
            "SELECT * FROM news WHERE is_public = 1 ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
    return cursor.fetchall()


# Game cycle management
@db_transaction
def distribute_district_resources(conn):
    """Distribute resources from controlled districts to players."""
    cursor = conn.cursor()
    # Get all districts that are controlled (60+ points)
    cursor.execute(
        """
        SELECT dc.district_id, dc.player_id, dc.control_points, 
               d.influence_resource, d.resources_resource, d.information_resource, d.force_resource
        FROM district_control dc
        JOIN districts d ON dc.district_id = d.district_id
        WHERE dc.control_points >= 60
        """
    )
    controlled_districts = cursor.fetchall()

    for district in controlled_districts:
        district_id, player_id, control_points, influence, resources, information, force = district
        # Update player resources
        if influence > 0:
            update_player_resources_internal(conn, player_id, "influence", influence)
        if resources > 0:
            update_player_resources_internal(conn, player_id, "resources", resources)
        if information > 0:
            update_player_resources_internal(conn, player_id, "information", information)
        if force > 0:
            update_player_resources_internal(conn, player_id, "force", force)


# Trading system queries
@db_transaction
def create_trade_offer(conn, sender_id, receiver_id, offer, request):
    """
    Create a new trade offer.

    Args:
        sender_id: ID of player making the offer
        receiver_id: ID of player receiving the offer
        offer: Dict of resources being offered {resource_type: amount}
        request: Dict of resources being requested {resource_type: amount}

    Returns:
        offer_id of created offer, or 0 if failed
    """
    try:
        cursor = conn.cursor()

        # Verify sender has sufficient resources
        sender_resources = get_player_resources(sender_id)
        if not sender_resources:
            logger.error(f"Sender {sender_id} not found or has no resources")
            return 0

        for resource, amount in offer.items():
            if sender_resources.get(resource, 0) < amount:
                logger.error(
                    f"Sender {sender_id} lacks {resource}: needs {amount}, has {sender_resources.get(resource, 0)}")
                return 0

        # Check if receiver exists
        cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (receiver_id,))
        if not cursor.fetchone():
            logger.error(f"Receiver {receiver_id} not found")
            return 0

        # Create the offer
        cursor.execute("""
            INSERT INTO trade_offers 
            (sender_id, receiver_id, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (sender_id, receiver_id, datetime.datetime.now().isoformat()))

        offer_id = cursor.lastrowid

        # Add offered resources
        for resource, amount in offer.items():
            cursor.execute("""
                INSERT INTO trade_resources
                (offer_id, resource_type, amount, is_offer)
                VALUES (?, ?, ?, 1)
            """, (offer_id, resource, amount))

        # Add requested resources
        for resource, amount in request.items():
            cursor.execute("""
                INSERT INTO trade_resources
                (offer_id, resource_type, amount, is_offer) 
                VALUES (?, ?, ?, 0)
            """, (offer_id, resource, amount))

        # Deduct resources from sender
        for resource, amount in offer.items():
            update_player_resources_internal(conn, sender_id, resource, -amount)

        return offer_id

    except Exception as e:
        logger.error(f"Error creating trade offer: {e}")
        return 0


@db_transaction
def accept_trade_offer(conn, offer_id, receiver_id):
    """
    Accept and execute a trade offer.

    Args:
        offer_id: ID of the trade offer
        receiver_id: ID of player accepting the offer

    Returns:
        bool: True if trade completed successfully
    """
    try:
        cursor = conn.cursor()

        # Verify offer exists and is pending
        cursor.execute("""
            SELECT sender_id, status 
            FROM trade_offers 
            WHERE offer_id = ? AND receiver_id = ? AND status = 'pending'
        """, (offer_id, receiver_id))

        offer = cursor.fetchone()
        if not offer:
            logger.error(f"Trade offer {offer_id} not found, not pending, or not for receiver {receiver_id}")
            return False

        sender_id = offer[0]

        # Get trade details
        cursor.execute("""
            SELECT resource_type, amount, is_offer 
            FROM trade_resources 
            WHERE offer_id = ?
        """, (offer_id,))

        resources = cursor.fetchall()
        offered = {}
        requested = {}

        for resource_type, amount, is_offer in resources:
            if is_offer:
                offered[resource_type] = amount
            else:
                requested[resource_type] = amount

        # Verify receiver has sufficient resources for the requested items
        receiver_resources = get_player_resources(receiver_id)
        if not receiver_resources:
            logger.error(f"Receiver {receiver_id} not found or has no resources")
            return False

        for resource, amount in requested.items():
            if receiver_resources.get(resource, 0) < amount:
                logger.error(
                    f"Receiver {receiver_id} lacks {resource}: needs {amount}, has {receiver_resources.get(resource, 0)}")
                return False

        # Execute trade
        # Transfer offered resources to receiver (already deducted from sender when offer was created)
        for resource, amount in offered.items():
            update_player_resources_internal(conn, receiver_id, resource, amount)

        # Transfer requested resources from receiver to sender
        for resource, amount in requested.items():
            update_player_resources_internal(conn, receiver_id, resource, -amount)
            update_player_resources_internal(conn, sender_id, resource, amount)

        # Update offer status
        cursor.execute("""
            UPDATE trade_offers 
            SET status = 'completed', completed_at = ?
            WHERE offer_id = ?
        """, (datetime.datetime.now().isoformat(), offer_id))

        return True

    except Exception as e:
        logger.error(f"Error accepting trade offer: {e}")
        return False