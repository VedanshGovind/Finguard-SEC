import random 
import hashlib 
import time 


OTP_EXPIREY_SECONDS = 400

def generate_otp():
    return str(random.randint(100000, 999999))

def hash_otp(otp: str):
    return hashlib.sha256(otp.encode()).hexdigest()

def is_expired(expires_at: float):
    return time.time() > expires_at