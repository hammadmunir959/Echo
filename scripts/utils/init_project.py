from database.db_manager import db_manager
from core.config import Config

def initialize_project():
    print("--- Echo Project Initialization ---")
    
    # 1. Check Dependencies
    if not Config.check_dependencies():
        print("Error: Dependency check failed.")
        return
    
    # 2. Initialize Directories
    Config.initialize_directories()
    
    # 3. Initialize Database
    try:
        db_manager.init_db()
        print("Success: Project initialized.")
    except Exception as e:
        print(f"Error: Database initialization failed: {e}")

if __name__ == "__main__":
    initialize_project()
