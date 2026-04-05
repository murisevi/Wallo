---
paths:
  - "backend/app/banking/**"
---
# Enable Banking API Rules

Base URL: https://api.enablebanking.com
Sandbox: Mock ASPSP (control panel configurable) + BBVA sandbox for Spain
Docs: https://enablebanking.com/docs/api/reference/

## Authentication — JWT RS256
- Generate JWT per request using PyJWT: pyjwt.encode(body, private_key, algorithm="RS256", headers={"kid": app_id})
- Header: {"typ": "JWT", "alg": "RS256", "kid": "<ENABLE_BANKING_APP_ID>"}
- Body: {"iss": "enablebanking.com", "aud": "api.enablebanking.com", "iat": <now>, "exp": <now+3600>}
- Max TTL: 86400s (24h). Recommended: 3600s (1h) per token.
- Private key loaded from .pem file at startup. NEVER commit .pem files.

## API Flow
1. GET /aspsps?country=es → banks identified by name+country (NOT a single ID)
2. POST /auth → start authorization → returns {url, authorization_id}
3. User redirected to url → authenticates at bank → redirected back with ?code=xxx
4. POST /sessions with {code} → returns {session_id, accounts[]}
5. GET /accounts/{uid}/balances — per account
6. GET /accounts/{uid}/transactions — uses continuation_key pagination

## Critical behaviors
- Balance types priority: ITAV (interim available, best) > XPCD (expected) > CLBD (closing booked)
- Amounts are STRINGS: {"amount": "1234.56", "currency": "EUR"} — always parse with Decimal.
- Transactions use continuation_key: keep calling until continuation_key is null.
- Empty list + continuation_key is VALID — must keep fetching.
- Session validity: up to 180 days. Set in POST /auth via access.valid_until.
- Rate limit: 4 background fetches/day per account. Unlimited if PSU headers provided.
- PSU headers (Psu-Ip-Address, Psu-User-Agent): include when user actively triggers data fetch.
- entry_reference is the transaction unique ID — but some banks don't provide it.
- credit_debit_indicator: "CRDT" = credit (money in), "DBIT" = debit (money out).

## Redirect flow
- redirect_url MUST be whitelisted in Enable Banking control panel app settings
- URL must EXACTLY match (including trailing slash or lack thereof)
- Enable Banking shows terms of service page before bank redirect
- After bank auth, user redirected to redirect_url?code=xxx
- code is single-use — use it immediately in POST /sessions

## Sandbox testing
- Mock ASPSP: configurable via control panel, no real bank credentials needed
- BBVA sandbox: real sandbox environment, credentials at https://enablebanking.com/docs/api/sandbox/
- Sandbox apps auto-activate, no contract needed
- Production (restricted mode): can link own accounts for testing without contract
