Routing
=======

ADS uses its own address system named AmsNetId to identify devices. The
assignment of a devices to an AmsNetId happens via routing. Routing is
handled differently on Windows and Linux and is explained for both
operating systems in the sections below.

To identify each side of a route we will use the terms *client* and
*target*. The *client* is your computer where pyads runs on. The
*target* is you plc or remote computer which you want to connect to.

Creating routes on Windows
--------------------------

On Windows you don’t need to manually add the routes with pyads but
instead you use the TwinCAT Router UI ( TcSystemManager) which comes
with the TwinCAT installation. Have a look at the TwinCAT documentation
on `infosys.beckhoff.com <https://infosys.beckhoff.de/english.php?content=../content/1033/TcSystemManager/Basics/TcSysMgr_AddRouteDialog.htm&id=>`__
for further details.

Creating routes on Linux
------------------------

To create a new route on Linux you can simply use the Connection class.
It connects to the target and creates a route to it on your client.

.. code:: python

   >>> import pyads
   >>> remote_ip = '192.168.0.100'
   >>> remote_ads = '5.12.82.20.1.1'
   >>> with pyads.Connection(remote_ads, pyads.PORT_TC3PLC1, remote_ip) as plc:
   >>>     plc.read_by_name('.TAG_NAME', pyads.PLCTYPE_INT)

.. note::

  You still need to create a route from the target to the client. You
  can do this manually on your target or you can use the function
  :py:func:`.add_route_to_plc` as explained below!

Get the AMS address of the local machine. This may need to be added to
the routing table of the remote machine.

.. note::

  On Linux machines at least one route must be added before the
  call to :py:func:`.get_local_address` will function properly.

Optionally, a local AmsNetId can be manually set before adding a route.
Set this to match the expected AMS ID in the remote machine’s routing
table.

.. code:: python

   >> > import pyads
   >> > pyads.open_port()
   >> > pyads.set_local_address('1.2.3.4.1.1')
   >> > pyads.close_port()

Adding routes to a target
-------------------------

ADS requires you to create a route in the routing tables of both your
client and your target. How you add a route to your client is handled in
the section above. To create a route on your target you can either use
TwinCAT or you can make use of the convenience function
:py:func:`.add_route_to_plc`.

Here is an example of adding a route to a target (e.g. remote plc) to
allow connections to a PC with the Hostname “MyPC”

.. warning::

  You need to open a port and set a local netid with :py:func:`.set_local_address` before you
  can use :py:func:`.add_route_to_plc`.

.. code:: python

   >>> import pyads
   >>> SENDER_AMS = '1.2.3.4.1.1'
   >>> PLC_IP = '192.168.0.100'
   >>> PLC_USERNAME = 'plc_username'
   >>> PLC_PASSWORD = 'plc_password'
   >>> ROUTE_NAME = 'RouteToMyPC'
   >>> HOSTNAME = 'MyPC'  # or IP
   >>>
   >>> pyads.open_port()
   >>> pyads.set_local_address(SENDER_AMS)
   >>> pyads.add_route_to_plc(SENDER_AMS, HOSTNAME, PLC_IP, PLC_USERNAME, PLC_PASSWORD, route_name=ROUTE_NAME)
   >>> pyads.close_port()

.. note::

    When adding the route in TwinCAT make sure to deactivate the unidirectional option.
