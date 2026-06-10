# API Documentation

## Rate Limits by Tier
- **Starter**: 100 requests/day, 10 requests/minute
- **Standard**: 1,000 requests/day, 100 requests/minute
- **Pro**: 10,000 requests/day, 500 requests/minute
- **Enterprise**: Custom limits, default 10,000 requests/minute

## API Versioning
- Current stable version: v2 (released September 2023)
- Legacy version: v1 (deprecated, sunset date: December 31, 2023)
- All new integrations must use v2

## v1 to v2 Breaking Changes
- New authentication header: `X-API-Key` replaced by `Authorization: Bearer <token>`
- New required header for all v2 requests: `X-Workspace-ID: <your_workspace_id>`
- All responses are now paginated (page, per_page, total fields added)
- Webhook signatures now use HMAC-SHA256 (v1 used MD5)
- Endpoint `/v1/events` renamed to `/v2/events`

## Authentication
- API keys are generated in Settings > API Keys
- Keys are scoped: read-only, read-write, or admin
- v2 endpoints require workspace ID header on every request

## Error Codes
- 400: Bad request — invalid parameters
- 401: Unauthorised — invalid or missing API key
- 403: Forbidden — insufficient scope for this endpoint
- 429: Rate limit exceeded — retry after X seconds (see Retry-After header)
- 500: Internal server error — contact support with request ID