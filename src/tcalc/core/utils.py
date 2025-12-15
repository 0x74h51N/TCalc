def is_number_token(tok: str) -> bool:
    try:
        float(tok)
        return True
    except Exception:
        return False
