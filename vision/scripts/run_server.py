"""Start the FastAPI server."""
import uvicorn
from vision.src.api.server import create_app


def main():
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()
