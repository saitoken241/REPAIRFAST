from passlib.context import CryptContext
import bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return bcrypt.hashpw(
        password.encode("utf-8"),   
        bcrypt.gensalt()
    ).decode("utf-8")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)