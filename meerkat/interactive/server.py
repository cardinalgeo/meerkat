import os
import threading
import time

import uvicorn

# By default, the local server will try to open on localhost, port 7860.
# If that is not available, then it will try 7861, 7862, ... 7959.
INITIAL_PORT_VALUE = int(os.getenv("MK_SERVER_PORT", "7860"))
TRY_NUM_PORTS = int(os.getenv("MK_NUM_PORTS", "100"))
LOCALHOST_NAME = os.getenv("MK_SERVER_NAME", "127.0.0.1")
MEERKAT_API_SERVER = "https://api.meerkat.app/v1/tunnel-request"


class Server(uvicorn.Server):
    """
    Taken from
    https://stackoverflow.com/questions/61577643/python-how-to-use-fastapi-and-uvicorn-run-without-blocking-the-thread
    and Gradio.
    """

    def install_signal_handlers(self):
        pass

    def run_in_thread(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        while not self.started:
            time.sleep(1e-3)

    def close(self):
        self.should_exit = True
        self.thread.join()
