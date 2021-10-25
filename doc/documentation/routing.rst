Routing
=======

ADS uses its own address system named AmsNetId to identify devices. The
assignment of a devices to an AmsNetId happens via routing. Routing is
handled differently on Windows and Linux and is explained for both
operating systems in the sections below.

To identify each side of a route we will use the terms *client* and
*target*. The *client* is your computer where pyads runs. The
*target* is your plc or remote computer which you want to connect to.

For the communication to work there needs to be routes in both directions, both
from the client to the target and from the target to the client. The route from
the client to the target is created when a Connection is created, but the route
from the target to the client needs to be created manually according to
instructions below.

Creating target to client route(s) on Windows
---------------------------------------------

On Windows you can't add the routes from the target to the client with pyads,
instead you use the TwinCAT Router UI (TcSystemManager) which comes with the
TwinCAT installation. Have a look at the TwinCAT documentation on
`infosys.beckhoff.com (TwinCAT2) <https://infosys.beckhoff.de/english.php?content=../content/1033/TcSystemManager/Basics/TcSysMgr_AddRouteDialog.htm&id=>`__
/ `infosys.beckhoff.com (TwinCAT3) <https://infosys.beckhoff.com/english.php?content=../content/1033/tc3_system/html/tcsysmgr_addroutedialog.htm&id=>`__
for further details.

.. note::

    When adding the route in TwinCAT make sure to deactivate the unidirectional option.

Creating target to client route(s) on Linux
-------------------------------------------

To create the required reverse route on Linux you use :py:func:`.add_route_to_plc`.
It connects to the target and creates a route from the target to your client.

Once the reverse route is created the client to target route is created by the
Connection class.

.. code:: python

   >>> import pyads
   >>> CLIENT_NETID = "192.168.1.10.1.1"  # The desired Ams Net Id of this device, choose freely
   >>> CLIENT_IP = "192.168.1.10"  # The IP address of this device
   >>> TARGET_IP = "192.168.1.11"  # The IP address of the target (most likely a PLC)
   >>> TARGET_USERNAME = "Administrator"  # Standard Beckhoff user name
   >>> TARGET_PASSWORD = "1"  # Standard Beckhoff password
   >>> ROUTE_NAME = "route-to-my-plc"  # A suitable description of the route
   >>> # Add a route from the target to the client
   >>> pyads.add_route_to_plc(
   >>>     CLIENT_NETID, CLIENT_IP, TARGET_IP, TARGET_USERNAME, TARGET_PASSWORD,
   >>>     route_name=ROUTE_NAME
   >>> )
   >>> # If the target ams net id is unknown this is an easy way to obtain it
   >>> TARGET_NET_ID = pyads.ads.adsGetNetIdForPLC('192.168.3.9')
   >>> # When creating the Connection the client to target route is created by the Connection class
   >>> with pyads.Connection(TARGET_NET_ID, pyads.PORT_TC3PLC1) as plc:
   >>>     plc.read_by_name('.TAG_NAME', pyads.PLCTYPE_INT)

