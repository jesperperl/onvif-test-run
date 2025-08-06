#!/usr/bin/env python3
"""
ONVIF Authentication Token Digest Calculator

This script computes an ONVIF authentication token digest using the formula:
Digest = B64ENCODE( SHA1( B64DECODE( Nonce ) + Date + Password ) )

The digest is used for WS-Security authentication in ONVIF communications.
"""

import base64
import hashlib
import datetime
# from typing import str


def compute_onvif_digest(nonce: str, date: str, password: str) -> str:
    """
    Compute ONVIF authentication token digest.

    Args:
        nonce: Base64-encoded nonce string
        date: ISO 8601 formatted date string (e.g., "2024-01-15T10:30:00Z")
        password: Plain text password

    Returns:
        Base64-encoded digest string
    """
    try:
        # Step 1: Base64 decode the nonce
        decoded_nonce = base64.b64decode(nonce)

        # Step 2: Concatenate decoded nonce + date + password
        # All components need to be bytes for SHA1 hashing
        date_bytes = date.encode('utf-8')
        password_bytes = password.encode('utf-8')
        combined = decoded_nonce + date_bytes + password_bytes

        # Step 3: Compute SHA1 hash
        sha1_hash = hashlib.sha1(combined).digest()

        # Step 4: Base64 encode the hash
        digest = base64.b64encode(sha1_hash).decode('utf-8')

        return digest

    except Exception as e:
        raise ValueError(f"Error computing digest: {e}")


def generate_current_timestamp() -> str:
    """
    Generate current UTC timestamp in ISO 8601 format.

    Returns:
        ISO 8601 formatted timestamp string
    """
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')


def generate_nonce() -> str:
    """
    Generate a random base64-encoded nonce.

    Returns:
        Base64-encoded nonce string
    """
    import os
    # Generate 16 random bytes and base64 encode them
    random_bytes = os.urandom(16)
    return base64.b64encode(random_bytes).decode('utf-8')


def main():
    """
    Example usage and interactive mode.
    """
    print("ONVIF Authentication Token Digest Calculator")
    print("=" * 50)

    # Example with hardcoded values
    print("\n1. Example with sample values:")
    sample_nonce = "MTIzNDU2Nzg5MDEyMzQ1Ng=="  # Base64 of "1234567890123456"
    sample_date = "2024-01-15T10:30:00.000Z"
    sample_password = "admin123"

    sample_digest = compute_onvif_digest(sample_nonce, sample_date, sample_password)

    print(f"   Nonce:    {sample_nonce}")
    print(f"   Date:     {sample_date}")
    print(f"   Password: {sample_password}")
    print(f"   Digest:   {sample_digest}")

    # Interactive mode
    print("\n2. Interactive mode:")
    try:
        # Option to generate new nonce and timestamp
        use_generated = input("\nGenerate new nonce and timestamp? (y/n): ").lower().strip()

        if use_generated == 'y':
            nonce = generate_nonce()
            date = generate_current_timestamp()
            print(f"Generated nonce: {nonce}")
            print(f"Generated date:  {date}")
        else:
            nonce = input("Enter base64-encoded nonce: ").strip()
            date = input("Enter date (ISO 8601 format): ").strip()

        password = input("Enter password: ").strip()

        if nonce and date and password:
            digest = compute_onvif_digest(nonce, date, password)
            print(f"\nComputed digest: {digest}")

            # Show the complete authentication token components
            print("\nComplete ONVIF authentication components:")
            print(f"Username: <your_username>")
            print(f"Password Digest: {digest}")
            print(f"Nonce: {nonce}")
            print(f"Created: {date}")
        else:
            print("Error: All fields are required.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
