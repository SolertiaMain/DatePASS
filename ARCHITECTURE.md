# DatePass architecture decisions

## Why a Lambda container image

The pass signer depends on `cryptography`, which includes native components. A Lambda container image keeps packaging deterministic while preserving the fully serverless execution model. The image uses AWS Lambda's Python 3.12 base image.

## Why API Gateway rather than direct S3 links

The URL shared with the recipient should stay stable. `/pass/{id}` resolves the invitation in DynamoDB and redirects to a short-lived S3 presigned URL. The S3 bucket never becomes public.

## Why GET does not mutate state

Messaging applications, security scanners and browser previews can request links automatically. `GET /accept/{id}` and `GET /decline/{id}` therefore render a review page; `POST /api/respond/{id}` performs the update.

## Phase 2: native Wallet push updates

Add the standard Apple Wallet web-service contract:

- Store `webServiceURL` and per-pass `authenticationToken` in `pass.json`.
- Create a device registration table keyed by device library identifier and pass serial number.
- Add register, unregister, changed-passes and latest-pass endpoints.
- Store APNs push tokens.
- Publish an event after invitation updates and invoke a notifier Lambda that calls APNs.
