from app.security import digest, hash_password, verify_password


def test_password_hash_and_digest() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong", hashed)
    assert digest("x") == digest("x")
    assert digest("x") != digest("y")
