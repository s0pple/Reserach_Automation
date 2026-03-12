import os

class BrowserProfileManager:
    """
    Manages isolated browser profiles for different AI agents (Personas).
    This allows parallel operations and avoids rate limits by spreading
    requests across different Google/Perplexity accounts.
    """
    def __init__(self, base_dir: str = "browser_sessions"):
        self.base_dir = os.path.abspath(base_dir)
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_profile_path(self, persona: str) -> str:
        """
        Returns the path to the specific user_data_dir for a persona.
        E.g., 'planner', 'critic', 'collector'.
        """
        profile_path = os.path.join(self.base_dir, persona.lower())
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)
        return profile_path

    def list_profiles(self):
        if not os.path.exists(self.base_dir):
            return []
        return [d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))]
