import requests
import json
from datetime import datetime, timedelta
import streamlit as st

class TokenManager:
    def __init__(self):
        # Access secrets from st.secrets instead of environment variables
        self.auth_url = st.secrets["AUTH_URL"]
        self.client_id = st.secrets["CLIENT_ID"]
        self.client_secret = st.secrets["CLIENT_SECRET"]
        self.username = st.secrets["USERNAME"]
        self.password = st.secrets["PASSWORD"]

        self._initialize_token_state()

    def _initialize_token_state(self):
        # Initialize all required session state variables with defaults
        if "access_token" not in st.session_state:
            try:
                # Try to get from secrets, but it might not exist
                st.session_state.access_token = st.secrets.get('ACCESS_TOKEN', None)
            except KeyError:
                st.session_state.access_token = None
                
        if "refresh_token" not in st.session_state:
            try:
                st.session_state.refresh_token = st.secrets.get('REFRESH_TOKEN', None)
            except KeyError:
                st.session_state.refresh_token = None
                
        if "token_expires_at" not in st.session_state:
            try:
                # Try to load expiry from secrets or set to None
                expires_str = st.secrets.get('TOKEN_EXPIRES_AT', None)
                if expires_str:
                    try:
                        st.session_state.token_expires_at = datetime.fromisoformat(expires_str)
                    except ValueError:
                        st.session_state.token_expires_at = None
                else:
                    st.session_state.token_expires_at = None
            except KeyError:
                st.session_state.token_expires_at = None
                
        if "last_refresh_time" not in st.session_state:
            st.session_state.last_refresh_time = None
            
        if "refresh_count_today" not in st.session_state:
            st.session_state.refresh_count_today = 0
            
        if "refresh_date" not in st.session_state:
            st.session_state.refresh_date = datetime.now().date()
            
        if "token_manager_initialized" not in st.session_state:
            st.session_state.token_manager_initialized = True

    def _save_tokens_to_persistent_storage(self, access_token, refresh_token, expires_at=None):
        """
        Save tokens to session state only (no file writing in Streamlit Cloud)
        In production, you might want to use a database or external storage
        """
        try:
            # Update session state
            st.session_state.access_token = access_token
            st.session_state.refresh_token = refresh_token
            if expires_at:
                st.session_state.token_expires_at = expires_at
            
            # Note: In Streamlit Cloud, you cannot write to files
            # Consider using a database or external storage service for persistence
            print("✅ Tokens saved to session state")
            
            # Optional: Display warning about token persistence
            if not hasattr(st.session_state, 'token_persistence_warning_shown'):
                st.session_state.token_persistence_warning_shown = True
                st.info("ℹ️ Tokens are stored in session state and will be lost when the session ends. Consider implementing database storage for production use.")
                
        except Exception as e:
            print(f"Warning: Could not save tokens: {e}")

    def _is_token_expired(self):
        """Check if the current token is expired"""
        # Ensure session state is initialized
        if not hasattr(st.session_state, 'access_token') or not st.session_state.access_token:
            print("❌ No access token available")
            return True
            
        if not hasattr(st.session_state, 'token_expires_at') or st.session_state.token_expires_at is None:
            print("⚠️ No expiry time set, assuming token is expired")
            return True
            
        # Use a smaller buffer to be more conservative
        buffer = timedelta(minutes=5)
        is_expired = datetime.now() >= (st.session_state.token_expires_at - buffer)
        
        if is_expired:
            print(f"❌ Token expired at {st.session_state.token_expires_at}")
        else:
            remaining_time = st.session_state.token_expires_at - datetime.now()
            print(f"✅ Token valid for {remaining_time}")
            
        return is_expired

    def _validate_token_with_api(self):
        """Optional: Validate token by making a test API call"""
        if not hasattr(st.session_state, 'access_token') or not st.session_state.access_token:
            return False
            
        # You can implement a simple API call to validate the token
        # This is optional and depends on your API having a validation endpoint
        return True  # Skip API validation for now
    
    def _can_refresh_token(self):
        """Check if we can safely refresh the token without hitting limits"""
        current_date = datetime.now().date()
        
        # Reset counter if it's a new day
        if st.session_state.refresh_date != current_date:
            st.session_state.refresh_count_today = 0
            st.session_state.refresh_date = current_date
        
        # Check daily limit
        daily_limit = 10
        if st.session_state.refresh_count_today >= daily_limit:
            st.warning(f"⚠️ Daily token refresh limit ({daily_limit}) reached. Please try again tomorrow.")
            return False
        
        # Prevent rapid successive refreshes (minimum 2 minutes between refreshes)
        if st.session_state.last_refresh_time:
            time_since_last_refresh = datetime.now() - st.session_state.last_refresh_time
            if time_since_last_refresh < timedelta(minutes=2):
                remaining_time = timedelta(minutes=2) - time_since_last_refresh
                st.info(f"Please wait {remaining_time.seconds // 60 + 1} more minutes before refreshing again.")
                return False
        
        return True

    def _refresh_access_token(self):
        """Private method to refresh the access token"""
        if not hasattr(st.session_state, 'refresh_token') or not st.session_state.refresh_token:
            raise Exception("No refresh token available")
        
        # Check if we can refresh without hitting limits
        if not self._can_refresh_token():
            raise Exception("Cannot refresh token due to rate limits")

        print("🔄 Refreshing access token...")
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": st.session_state.refresh_token
        }

        try:
            response = requests.post(self.auth_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token", st.session_state.refresh_token)
            
            expires_in = data.get("expires_in", 3600)
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Update refresh tracking
            st.session_state.last_refresh_time = datetime.now()
            st.session_state.refresh_count_today += 1

            # Save to persistent storage (session state in this case)
            self._save_tokens_to_persistent_storage(
                access_token, 
                new_refresh_token,
                expires_at
            )

            print(f"✅ Access token refreshed successfully. ({st.session_state.refresh_count_today} refreshes today)")
            print(f"✅ New token expires at: {st.session_state.token_expires_at}")
            
            return st.session_state.access_token

        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            raise Exception(f"Token refresh failed: {e}")

    def get_valid_access_token(self):
        """Get a valid access token, only refreshing if necessary"""
        print("🔍 Checking token validity...")
        
        # Ensure session state is initialized
        if not hasattr(st.session_state, 'access_token'):
            self._initialize_token_state()
        
        # First check if token exists and is not expired based on timestamp
        if st.session_state.access_token and not self._is_token_expired():
            print("✅ Using existing valid token")
            return st.session_state.access_token
        
        # If token is expired or doesn't exist, try to refresh
        print("🔄 Token needs refresh...")
        try:
            return self._refresh_access_token()
        except Exception as e:
            st.error(f"Failed to refresh token: {e}")
            print(f"❌ Failed to refresh token: {e}")
            
            # Only return existing token if absolutely necessary
            if hasattr(st.session_state, 'access_token') and st.session_state.access_token:
                st.warning("Using potentially expired token as fallback")
                return st.session_state.access_token
            else:
                return None

    def manual_refresh_token(self):
        """Public method for manual token refresh (for UI buttons)"""
        try:
            print("🔄 Manual token refresh requested...")
            return self._refresh_access_token()
        except Exception as e:
            st.error(f"Manual token refresh failed: {e}")
            print(f"❌ Manual token refresh failed: {e}")
            return None

    def get_token_status(self):
        """Get current token status for debugging"""
        # Ensure session state is initialized
        if not hasattr(st.session_state, 'token_manager_initialized'):
            self._initialize_token_state()
            
        status = {
            "has_access_token": bool(getattr(st.session_state, 'access_token', None)),
            "has_refresh_token": bool(getattr(st.session_state, 'refresh_token', None)),
            "expires_at": getattr(st.session_state, 'token_expires_at', None),
            "is_expired": self._is_token_expired(),
            "refresh_count_today": getattr(st.session_state, 'refresh_count_today', 0),
            "last_refresh_time": getattr(st.session_state, 'last_refresh_time', None)
        }
        return status

    def make_authenticated_request(self, method, url, **kwargs):
        """Make an authenticated request with automatic token refresh"""
        print(f"🌐 Making {method} request to {url}")
        
        token = self.get_valid_access_token()
        if not token:
            st.error("Unable to obtain valid access token.")
            return None

        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        kwargs['headers'] = headers

        try:
            response = requests.request(method, url, **kwargs)
            
            # If we get 401, the token might be invalid despite our checks
            if response.status_code == 401:
                print("⚠️ Received 401 response, token might be invalid")
                st.warning("Token appears to be invalid. Attempting to refresh...")
                
                # Force refresh by setting token as expired
                st.session_state.token_expires_at = datetime.now() - timedelta(minutes=1)
                
                # Try to get a fresh token
                token = self.get_valid_access_token()
                
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    kwargs['headers'] = headers
                    response = requests.request(method, url, **kwargs)
                    
                    if response.status_code == 401:
                        st.error("Still unauthorized after token refresh. Please check your credentials.")
                        print("❌ Still unauthorized after token refresh")
                    else:
                        print("✅ Request successful after token refresh")
                else:
                    st.error("Failed to refresh token for retry.")
                    print("❌ Failed to refresh token for retry")
            else:
                print(f"✅ Request completed with status: {response.status_code}")
            
            return response
            
        except requests.exceptions.RequestException as e:
            st.error(f"Request error: {e}")
            print(f"❌ Request error: {e}")
            return None

# Example usage function to show token status
def display_token_status(token_manager):
    """Helper function to display token status in Streamlit UI"""
    status = token_manager.get_token_status()
    
    st.subheader("Token Status")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Has Access Token:** {'✅' if status['has_access_token'] else '❌'}")
        st.write(f"**Has Refresh Token:** {'✅' if status['has_refresh_token'] else '❌'}")
        st.write(f"**Token Expired:** {'❌' if status['is_expired'] else '✅'}")
    
    with col2:
        st.write(f"**Expires At:** {status['expires_at']}")
        st.write(f"**Refreshes Today:** {status['refresh_count_today']}")
        st.write(f"**Last Refresh:** {status['last_refresh_time']}")
    
    if st.button("Manual Refresh Token"):
        token_manager.manual_refresh_token()
        st.rerun()
