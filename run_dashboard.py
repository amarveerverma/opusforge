import argparse
from clipper.web_app import start_server


def main():
    parser = argparse.ArgumentParser(description="Launch Opus Clip Local Web Dashboard")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
