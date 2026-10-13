import http.server
import socketserver
from pathlib import Path
from urllib.parse import unquote, urlsplit


PROJECT_DIR = Path(__file__).resolve().parent
WEB_DIR = PROJECT_DIR / "web"
TEMPLATES_DIR = PROJECT_DIR / "templates"


class FrontendHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        # Serve the web folder as the website root.
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def translate_path(self, path):
        # Read only the URL path.
        url_path = unquote(urlsplit(path).path)

        # Website home page.
        if url_path == "/":
            url_path = "/index.html"

        # Clean chat URL:
        # /chat -> templates/chat.html
        if url_path in ("/chat", "/chat/"):
            return str(TEMPLATES_DIR / "chat.html")

        parts = url_path.lstrip("/").split("/")

        # Block hidden files and directory traversal.
        if any(
            part in ("", ".", "..") or part.startswith(".")
            for part in parts
        ):
            return str(PROJECT_DIR / "__blocked__")

        # Allow frontend files inside templates.
        if parts[0] == "templates":
            base = TEMPLATES_DIR
            relative_parts = parts[1:]
        else:
            base = WEB_DIR
            relative_parts = parts

        # Block empty paths.
        if not relative_parts:
            return str(PROJECT_DIR / "__blocked__")

        target = base.joinpath(*relative_parts).resolve()

        # Prevent access outside the allowed folder.
        if not target.is_relative_to(base.resolve()):
            return str(PROJECT_DIR / "__blocked__")

        return str(target)

    def list_directory(self, path):
        # Disable directory browsing.
        self.send_error(
            403,
            "Directory listing is disabled"
        )
        return None


def main():
    host = "127.0.0.1"
    port = 5500

    with socketserver.TCPServer(
        (host, port),
        FrontendHandler
    ) as server:
        print(
            f"Website running at http://{host}:{port}"
        )
        server.serve_forever()


if __name__ == "__main__":
    main()