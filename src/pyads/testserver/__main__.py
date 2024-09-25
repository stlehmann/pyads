"""The testserver run script.

:author: Roberto Roos
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2021-04-09

"""

import argparse

from .testserver import AdsTestServer, AdvancedHandler, BasicHandler, AbstractHandler


def main() -> None:
    """Main function (keep variable out of global scope)"""

    parser = argparse.ArgumentParser(description='Run an ADS Testserver')
    parser.add_argument("--host", default="127.0.0.1", help="host IP, default: 127.0.0.1")
    parser.add_argument("-p", "--port", default=48898, help="binding port, default: 48898", type=int)
    parser.add_argument('--handler', choices=['basic', 'advanced'], default='advanced',
                        help="testserver handler, default: advanced")
    args = parser.parse_args()

    handler: AbstractHandler
    if args.handler == 'basic':
        handler = BasicHandler()
    else:
        handler = AdvancedHandler()

    server = AdsTestServer(
        ip_address=args.host,
        port=args.port,
        handler=handler
    )

    # noinspection PyBroadException
    try:
        print('Starting testserver...')
        server.start()
        print('Running testserver at {}:{}'.format(server.ip_address, server.port))
        server.join()
    except:
        server.close()

    print('Testserver closed')


if __name__ == "__main__":
    main()
