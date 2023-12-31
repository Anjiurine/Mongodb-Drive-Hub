import sys
import asyncio
from service import run_server_mode, run_cli_mode

if __name__ == "__main__":
    if "-s" in sys.argv or "--server" in sys.argv:
        asyncio.run(run_server_mode())
    else:
        run_cli_mode()