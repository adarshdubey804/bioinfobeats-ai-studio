from app.core.security import hash_password,verify_password,create_access_token
import jwt
from app.core.config import settings
from app.core.security import ALGORITHM
def test_password_hash_round_trip():
 hashed=hash_password('long-test-password-123');assert hashed!='long-test-password-123';assert verify_password('long-test-password-123',hashed)
def test_access_token_contains_subject():
 token=create_access_token('user-123');assert jwt.decode(token,settings.secret_key,algorithms=[ALGORITHM])['sub']=='user-123'
