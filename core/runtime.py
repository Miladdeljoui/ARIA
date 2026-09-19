import os
import socket


def internet_available(timeout: float = 2.0) -> bool:
    try:
        sock = socket.create_connection(("1.1.1.1", 53), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def choose_backend(cloud_url: str, local_url: str, timeout: float = 2.0) -> str:
    if internet_available(timeout=timeout):
        return cloud_url.rstrip("/")

    return local_url.rstrip("/")


def configured_cloud_url() -> str:
    return os.getenv("ARIA_CLOUD_URL", "").strip()
