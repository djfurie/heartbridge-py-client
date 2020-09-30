#!/usr/bin/env python

import heartbridge
import time
import logging
import signal
import argparse

LOGGING_FORMAT = '%(asctime)s :: %(name)s (%(levelname)s) -- %(message)s'
logging.basicConfig(format=LOGGING_FORMAT, level=logging.DEBUG)

listening = False


def sigint_handler(sig, frame):
    global listening
    logging.error("Ctrl+C pressed! Disconnecting!")
    listening = False


def main():
    global listening
    signal.signal(signal.SIGINT, sigint_handler)

    parser = argparse.ArgumentParser(description="HeartBridge WebSocket API Client")
    parser.add_argument('-s', '--subscribe', metavar="performance_id", type=str.upper,
                        help="Subscribe to a given performance id")

    args = parser.parse_args()

    # c = heartbridge.WSClient("wss://heartbridge.furiousenterprises.net")
    c = heartbridge.WSClient("ws://localhost:8000")
    listening = True

    if args.subscribe:
        c.subscribe(args.subscribe)

        while listening:
            time.sleep(0.5)
            if not c.is_connected:
                break

    c.close()


if __name__ == '__main__':
    main()
