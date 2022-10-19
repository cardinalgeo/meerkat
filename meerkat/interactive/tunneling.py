"""
This file providdes remote forwarding 
"""
import re
import subprocess
import time
from tempfile import mkstemp

PORT = "2222"
DOMAIN = "meerkat.wiki"

def setup_tunnel(local_port: int, subdomain: str) -> str:
    """
    """
    PORT = "2222"
    DOMAIN = "meerkat.wiki"

    # open a temporary file to write the output of the npm process
    out_file, out_path = mkstemp(suffix=".out")
    err_file, err_path = mkstemp(suffix=".err")
    subprocess.Popen(
        [
            "ssh",
            # need to use the -T arg to avoid corruption of the users terminal
            "-T",
            "-p",
            PORT,
            # sish does not support ControlMaster as discussed in this issue
            # https://github.com/antoniomika/sish/issues/252
            "-o", 
            "ControlMaster=no", 
            "-R",
            f"{subdomain}:80:localhost:{local_port}",
            DOMAIN
        ],
        stdout=out_file,
        stderr=err_file,
    )

    MAX_WAIT = 10
    for i in range(MAX_WAIT):
        time.sleep(0.5)

        # this checks whether or not the tunnel has successfully been established
        # and the subdomain is printed to out 
        match = re.search(
            f"http://(.*).{DOMAIN}", open(out_path, "r").read()
        )
        if match is not None:
            break
    
    if match is None:
        raise ValueError(
            f"Failed to establish tunnel: out={open(out_path, 'r').read()} err={open(err_path, 'r').read()}"
        )
    actual_subdomain = match.group(1)
    
    if actual_subdomain != subdomain:
        # need to check because the requested subdomain may already be in use
        print(
            f"Subdomain {subdomain} is not available. " 
            f"Using {actual_subdomain} instead."
        )

    return f"{actual_subdomain}.{DOMAIN}"

