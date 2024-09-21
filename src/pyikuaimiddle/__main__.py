import logging

from .app import app

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app.run(port=19198, debug=True, threaded=True)