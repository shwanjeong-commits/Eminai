import bootstrap  # noqa: F401

import base64

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def main() -> None:
    vapid = Vapid()
    vapid.generate_keys()
    private_value = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    public_value = vapid.public_key.public_bytes(
        encoding=Encoding.X962,
        format=PublicFormat.UncompressedPoint,
    )
    print("Add these values to .env:")
    print(f"VAPID_PUBLIC_KEY={b64url(public_value)}")
    print(f"VAPID_PRIVATE_KEY={b64url(private_value)}")
    print("VAPID_SUBJECT=mailto:your-email@example.com")


if __name__ == "__main__":
    main()
