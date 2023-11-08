#!/usr/bin/python3 -u

import argparse
import drovecli
import droveclient

def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(prog="drove")

    parser.add_argument("--config", "-c", help="Configuration file for drove client")
    parser.add_argument("--endpoint", "-e", help="Drove endpoint. (For example: https://drove.test.com)")
    parser.add_argument("--auth-header", "-t", dest="auth_header", help="Authorization header value for the provided drove endpoint")
    parser.add_argument("--insecure", "-i", help="Do not verify SSL cert for server")
    parser.add_argument("--username", "-u", help="Drove cluster username")
    parser.add_argument("--password", "-p", help="Drove cluster password")
    return parser

def run():
    parser = build_parser()
    try:
        drovecli.DroveCli(parser).run()
    except (BrokenPipeError, IOError, KeyboardInterrupt):
        pass
    except Exception as e:
        print("error: " + str(e))
        parser.print_help()

if __name__ == '__main__':
    run()