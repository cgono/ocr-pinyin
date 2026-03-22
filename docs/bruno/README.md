# Bruno Import

Use Bruno's OpenAPI URL import so the collection stays in sync with the live API contract.

## Import Steps

1. Start the backend on `http://localhost:8000`.
2. In Bruno, create or open a workspace.
3. Open the collections menu and choose `Import Collection`.
4. Select `OpenAPI`.
5. Choose the `URL` import option.
6. Enter `http://localhost:8000/openapi.json`.
7. Complete the import and save the generated collection.

## Why This Repo Uses Import Instead Of Checked-In `.bru` Requests

- Bruno officially supports importing OpenAPI v3 specs from a URL.
- Importing from `http://localhost:8000/openapi.json` keeps requests aligned with the current FastAPI schema as endpoints evolve.
- The OpenAPI schema now declares `http://localhost:8000` as the local development server, so the imported requests resolve against the expected base URL.

## Reference

- OpenAPI spec URL: `http://localhost:8000/openapi.json`
- Swagger UI: `http://localhost:8000/docs`
