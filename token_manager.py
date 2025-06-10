import requests
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

class TokenManager:
    def __init__(self):
        self.auth_url = os.getenv('AUTH_URL')
        self.client_id = os.getenv('CLIENT_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')

        self._initialize_token_state()

    def _initialize_token_state(self):
        if "access_token" not in st.session_state:
            st.session_state.access_token = os.getenv('ACCESS_TOKEN')
        if "refresh_token" not in st.session_state:
            st.session_state.refresh_token = os.getenv('REFRESH_TOKEN')
        if "token_expires_at" not in st.session_state:
            # Try to load expiry from env or set to None
            expires_str = os.getenv('TOKEN_EXPIRES_AT')
            if expires_str:
                try:
                    st.session_state.token_expires_at = datetime.fromisoformat(expires_str)
                except ValueError:
                    st.session_state.token_expires_at = None
            else:
                st.session_state.token_expires_at = None
        if "last_refresh_time" not in st.session_state:
            st.session_state.last_refresh_time = None
        if "refresh_count_today" not in st.session_state:
            st.session_state.refresh_count_today = 0
        if "refresh_date" not in st.session_state:
            st.session_state.refresh_date = datetime.now().date()

    def _save_tokens_to_env(self, access_token, refresh_token, expires_at=None):
        try:
            env_path = '.env'
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()

                updated_lines = []
                found_access = False
                found_refresh = False
                found_expires = False

                for line in lines:
                    if line.startswith('ACCESS_TOKEN='):
                        updated_lines.append(f'ACCESS_TOKEN={access_token}\n')
                        found_access = True
                    elif line.startswith('REFRESH_TOKEN='):
                        updated_lines.append(f'REFRESH_TOKEN={refresh_token}\n')
                        found_refresh = True
                    elif line.startswith('TOKEN_EXPIRES_AT='):
                        if expires_at:
                            updated_lines.append(f'TOKEN_EXPIRES_AT={expires_at.isoformat()}\n')
                        found_expires = True
                    else:
                        updated_lines.append(line)

                if not found_access:
                    updated_lines.append(f'ACCESS_TOKEN={access_token}\n')
                if not found_refresh:
                    updated_lines.append(f'REFRESH_TOKEN={refresh_token}\n')
                if not found_expires and expires_at:
                    updated_lines.append(f'TOKEN_EXPIRES_AT={expires_at.isoformat()}\n')

                with open(env_path, 'w') as f:
                    f.writelines(updated_lines)
                    
                print("✅ Tokens saved to .env file")
        except Exception as e:
            print(f"Warning: Could not save tokens to .env file: {e}")

    def _is_token_expired(self):
        """Check if the current token is expired"""
        if not st.session_state.access_token:
            print("❌ No access token available")
            return True
            
        if st.session_state.token_expires_at is None:
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
        if not st.session_state.access_token:
            return False
            
        # You can implement a simple API call to validate the token
        # This is optional and depends on your API having a validation endpoint
        # Example:
        # try:
        #     response = requests.get(
        #         "YOUR_API_VALIDATION_ENDPOINT",
        #         headers={"Authorization": f"Bearer {st.session_state.access_token}"}
        #     )
        #     return response.status_code == 200
        # except:
        #     return False
        
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
        if not st.session_state.refresh_token:
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

            st.session_state.access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")
            if new_refresh_token:
                st.session_state.refresh_token = new_refresh_token

            expires_in = data.get("expires_in", 3600)
            st.session_state.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Update refresh tracking
            st.session_state.last_refresh_time = datetime.now()
            st.session_state.refresh_count_today += 1

            # Save to .env file
            self._save_tokens_to_env(
                st.session_state.access_token, 
                st.session_state.refresh_token,
                st.session_state.token_expires_at
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
            if st.session_state.access_token:
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
        status = {
            "has_access_token": bool(st.session_state.access_token),
            "has_refresh_token": bool(st.session_state.refresh_token),
            "expires_at": st.session_state.token_expires_at,
            "is_expired": self._is_token_expired() if st.session_state.access_token else True,
            "refresh_count_today": st.session_state.refresh_count_today,
            "last_refresh_time": st.session_state.last_refresh_time
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