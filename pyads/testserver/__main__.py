import argparse

from .testserver import AdsTestServer, AdvancedHandler, BasicHandler


def main():
    """Main function (keep variable out of global scope)"""

    parser = argparse.ArgumentParser(description='Run an ADS Testserver')
    parser.add_argument(
        '--handler',
        choices=['basic', 'advanced'],
        default='advanced'
    )
    args = parser.parse_args()

    if args.handler == 'basic':
        handler = BasicHandler()
    else:
        handler = AdvancedHandler()

    server = AdsTestServer(handler=handler)

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
