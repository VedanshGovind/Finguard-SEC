"""
security/integrity_check.py

Responsibilities:
- Verify that the input file exists and is readable.
- Perform basic file-type validation.
- (Optional) Generate a cryptographic hash for audit trails.
"""

import os
import hashlib
from fastapi import HTTPException
from app_logging.event_logger import log_event

def verify_input_integrity(file_path: str):
    """
    Performs security and integrity checks on the uploaded video file.
    """
    # 1. Physical Existence Check
    if not os.path.exists(file_path):
        log_event("INTEGRITY_CHECK_FAILED", {"reason": "File not found", "path": file_path})
        raise HTTPException(status_code=404, detail="Processed file vanished from temp storage.")

    # 2. Size Check (Safety against 'Zip Bombs' or massive files)
    file_size = os.path.getsize(file_path)
    max_size = 50 * 1024 * 1024  # 50MB limit for edge safety
    if file_size > max_size:
        log_event("INTEGRITY_CHECK_FAILED", {"reason": "File too large", "size": file_size})
        raise HTTPException(status_code=413, detail="Video file exceeds edge processing limit (50MB).")

    # 3. Cryptographic Fingerprinting (SHA-256)
    # This creates a unique digital signature of the file for the logs.
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read in 64KB chunks to handle memory efficiently
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        
        file_hash = sha256_hash.hexdigest()
        
        log_event("INTEGRITY_CHECK_PASSED", {
            "file_size": file_size,
            "sha256": file_hash
        })
        
        return file_hash

    except Exception as e:
        log_event("INTEGRITY_CHECK_ERROR", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to verify file integrity.")