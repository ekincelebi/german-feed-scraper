from supabase import create_client, Client
from app.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseDatabase:
    """Supabase database connection manager."""

    def __init__(self):
        self.client: Client = None

    def connect(self) -> Client:
        """Initialize and return Supabase client."""
        if not self.client:
            try:
                self.client = create_client(
                    supabase_url=settings.supabase_url,
                    supabase_key=settings.supabase_key
                )
                logger.info("Successfully connected to Supabase")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
                raise
        return self.client

    def get_client(self) -> Client:
        """Get the Supabase client, creating connection if needed."""
        if not self.client:
            return self.connect()
        return self.client


# Global database instance
db = SupabaseDatabase()


def get_db() -> Client:
    """Get Supabase client instance."""
    return db.get_client()
