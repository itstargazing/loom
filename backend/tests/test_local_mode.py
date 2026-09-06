"""Hostname matching for local-only sensitive domains."""

from app.services.local_mode import matches_local_domain, normalize_domain_pattern


def test_exact_host_match():
    assert matches_local_domain(
        "https://bank.example.com/login", ["bank.example.com"]
    )


def test_subdomain_match():
    assert matches_local_domain(
        "https://secure.bank.example.com/app", ["bank.example.com"]
    )


def test_gov_suffix():
    assert matches_local_domain("https://irs.gov/forms", [".gov", "gov"])


def test_unrelated_host_does_not_match():
    assert not matches_local_domain(
        "https://shop.example.com/cart", ["bank.example.com", "gov"]
    )


def test_normalize_strips_scheme_and_path():
    assert normalize_domain_pattern("https://Bank.Example.com/path/") == "bank.example.com"
