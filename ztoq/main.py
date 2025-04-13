import uvicorn

from ztoq.core.services import get_openapi_spec


def main():
    """Main entry point for ZTOQ application."""
    # Preload OpenAPI spec to cache it
    spec = get_openapi_spec()
    print(f"Loaded OpenAPI spec: {spec.title} v{spec.version}")

    # Start FastAPI application
    uvicorn.run(
        "ztoq.api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
