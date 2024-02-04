VERSION = (3, 0, 0, "pre")

def version_str() -> str:
    return f"{VERSION[0]}.{VERSION[1]}.{VERSION[2]}{VERSION[3]}"
