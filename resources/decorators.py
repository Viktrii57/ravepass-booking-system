from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def admin_required(fn):
    """
    Use *in addition to* @jwt_required() (or combined, see below).
    Checks the 'role' claim embedded in the JWT at login time.
    Returns 403 (not 401) — the user IS authenticated, just not authorized.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "admin":
            return {"error": "Admin privileges required"}, 403
        return fn(*args, **kwargs)
    return wrapper