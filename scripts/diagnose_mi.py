#!/usr/bin/env python3
"""Diagnose managed identity token acquisition inside Azure Container Apps.

Run inside the container (via `az containerapp exec` or as a temp CMD):
    python scripts/diagnose_mi.py

Tests whether the managed identity can get tokens for various scopes.
Prints results to stdout for log inspection.
"""

import os
import sys
import json
import time


def check_env():
    """Print relevant environment variables."""
    keys = [
        "AZURE_CLIENT_ID",
        "AZURE_AUTHORITY_HOST",
        "AZURE_AI_PROJECT_ENDPOINT",
        "AZURE_OPENAI_TOKEN_SCOPE",
        "IDENTITY_ENDPOINT",
        "IDENTITY_HEADER",
        "MSI_ENDPOINT",
        "MSI_SECRET",
    ]
    print("=== Environment ===")
    for k in keys:
        v = os.environ.get(k, "<not set>")
        # Mask secrets
        if "SECRET" in k or "HEADER" in k:
            v = v[:8] + "..." if len(v) > 8 else v
        print(f"  {k} = {v}")
    print()


def test_scope_with_requests(scope: str, client_id: str | None):
    """Test token acquisition using raw HTTP to the identity endpoint (no SDK)."""
    identity_endpoint = os.environ.get("IDENTITY_ENDPOINT")
    identity_header = os.environ.get("IDENTITY_HEADER")

    if not identity_endpoint or not identity_header:
        return None, "IDENTITY_ENDPOINT or IDENTITY_HEADER not set"

    try:
        import urllib.request
        import urllib.parse

        # Strip /.default for the resource parameter
        resource = scope.replace("/.default", "")

        params = {"api-version": "2019-08-01", "resource": resource}
        if client_id:
            params["client_id"] = client_id

        url = f"{identity_endpoint}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"X-IDENTITY-HEADER": identity_header})

        start = time.time()
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = time.time() - start
            body = json.loads(resp.read())
            token = body.get("access_token", "")
            expires = body.get("expires_on", "?")
            return True, f"OK ({elapsed:.2f}s, token_len={len(token)}, expires_on={expires})"
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        body = e.read().decode("utf-8", errors="replace")
        return False, f"HTTP {e.code} ({elapsed:.2f}s): {body[:500]}"
    except Exception as e:
        return False, f"Error: {e}"


def test_scope_with_sdk(scope: str, authority: str | None, client_id: str | None):
    """Test token acquisition using azure-identity SDK."""
    try:
        from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

        # Test 1: ManagedIdentityCredential directly
        kwargs = {}
        if client_id:
            kwargs["client_id"] = client_id
        cred = ManagedIdentityCredential(**kwargs)
        start = time.time()
        try:
            token = cred.get_token(scope)
            elapsed = time.time() - start
            mi_result = f"OK ({elapsed:.2f}s, token_len={len(token.token)})"
        except Exception as e:
            elapsed = time.time() - start
            mi_result = f"FAILED ({elapsed:.2f}s): {e}"

        # Test 2: DefaultAzureCredential
        dac_kwargs = {}
        if authority:
            dac_kwargs["authority"] = authority
        cred2 = DefaultAzureCredential(**dac_kwargs)
        start = time.time()
        try:
            token2 = cred2.get_token(scope)
            elapsed = time.time() - start
            dac_result = f"OK ({elapsed:.2f}s, token_len={len(token2.token)})"
        except Exception as e:
            elapsed = time.time() - start
            dac_result = f"FAILED ({elapsed:.2f}s): {e}"

        return mi_result, dac_result
    except ImportError:
        return "azure-identity not installed", "azure-identity not installed"


def main():
    print("=" * 60)
    print("Managed Identity Token Diagnostic")
    print("=" * 60)
    print()

    check_env()

    client_id = os.environ.get("AZURE_CLIENT_ID")
    authority = os.environ.get("AZURE_AUTHORITY_HOST")

    scopes = [
        "https://cognitiveservices.azure.us/.default",
        "https://cognitiveservices.azure.com/.default",
        "https://ai.azure.com/.default",
        "https://management.usgovcloudapi.net/.default",
        "https://management.azure.com/.default",
    ]

    # Raw HTTP tests (bypass SDK entirely)
    print("=== Raw HTTP Token Tests (no SDK) ===")
    for scope in scopes:
        ok, msg = test_scope_with_requests(scope, client_id)
        status = "PASS" if ok else ("SKIP" if ok is None else "FAIL")
        print(f"  [{status}] {scope}")
        print(f"         {msg}")
    print()

    # SDK tests
    print("=== SDK Token Tests ===")
    for scope in scopes:
        mi_result, dac_result = test_scope_with_sdk(scope, authority, client_id)
        print(f"  Scope: {scope}")
        print(f"    ManagedIdentityCredential: {mi_result}")
        print(f"    DefaultAzureCredential:    {dac_result}")
    print()

    print("=== Done ===")


if __name__ == "__main__":
    main()
