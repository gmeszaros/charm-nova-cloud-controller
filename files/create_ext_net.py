#!/usr/bin/python

from quantumclient.v2_0 import client
import optparse
import os
import sys
import logging


usage = """Usage: %prog [options] ext_net_name

For example:

  %prog -g 192.168.21.1 -c 192.168.21.0/25 \\
      -f 192.168.21.100:192.168.21.200 ext_net
"""

if __name__ == '__main__':
    parser = optparse.OptionParser(usage)
    parser.add_option("-d", "--debug",
                      help="Enable debug logging",
                      dest="debug", action="store_true", default=False)
    parser.add_option("-g", "--gateway",
                      help="Default gateway to use.",
                      dest="default_gateway", action="store", default=None)
    parser.add_option("-c", "--cidr",
                      help="CIDR of external network.",
                      dest="cidr", action="store", default=None)
    parser.add_option("-f", "--floating-range",
                      help="Range of floating IP's to use (separated by :).",
                      dest="floating_range", action="store", default=None)
    (opts, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    if opts.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    net_name = args[0]
    subnet_name = '{}_subnet'.format(net_name)

    if (opts.floating_range):
        (start_floating_ip, end_floating_ip) = opts.floating_range.split(':')
    else:
        start_floating_ip = None
        end_floating_ip = None

    quantum = client.Client(username=os.environ['OS_USERNAME'],
                            password=os.environ['OS_PASSWORD'],
                            tenant_name=os.environ['OS_TENANT_NAME'],
                            auth_url=os.environ['OS_AUTH_URL'])

    networks = quantum.list_networks(name=net_name)
    if len(networks['networks']) == 0:
        logging.info('Configuring external bridge')
        network_msg = {
            'name': net_name,
            'router:external': True
        }
        logging.info('Creating new external network definition: %s',
                     net_name)
        network = quantum.create_network({'network': network_msg})['network']
        logging.info('New external network created: %s', network['id'])
    else:
        logging.warning('Network %s already exists.', net_name)
        network = networks['networks'][0]

    subnets = quantum.list_subnets(name=subnet_name)
    if len(subnets['subnets']) == 0:
        subnet_msg = {
            'name': subnet_name,
            'network_id': network['id'],
            'enable_dhcp': False,
            'ip_version': 4
        }

        if opts.default_gateway:
            subnet_msg['gateway_ip'] = opts.default_gateway
        if opts.cidr:
            subnet_msg['cidr'] = opts.cidr
        if (start_floating_ip and end_floating_ip):
            subnet_msg['allocation_pools'] = [
                    {
                    'start': start_floating_ip,
                    'end': end_floating_ip
                    }
             ]

        logging.info('Creating new subnet for %s', net_name)
        subnet = quantum.create_subnet({'subnet': subnet_msg})['subnet']
        logging.info('New subnet created: %s', subnet['id'])
    else:
        logging.warning('Subnet %s already exists.', subnet_name)
        subnet = subnets['subnets'][0]

    routers = quantum.list_routers(name='provider-router')
    if len(routers['routers']) == 0:
        logging.info('Creating provider router for external network access')
        router = quantum.create_router(
                        {'router': {'name': 'provider-router'}}
                        )['router']
        logging.info('New router created: %s', (router['id']))
    else:
        logging.warning('Router provider-router already exists.')
        router = routers['routers'][0]

    ports = quantum.list_ports(device_owner='network:router_gateway',
                               network_id=network['id'])
    if len(ports['ports']) == 0:
        logging.info('Plugging router into ext_net')
        router = \
            quantum.add_gateway_router(
                            router=router['id'],
                            body={'network_id': network['id']}
                            )
        logging.info('Router connected to %s', net_name)
    else:
        logging.warning('Router already connect to %s', net_name)
