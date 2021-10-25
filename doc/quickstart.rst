Quickstart
----------

.. important::

    You need to create routes on your client pc and on your target plc via TwinCAT **before
    any communication can take place**. If you are on Windows you can use the TwinCAT router.
    For Linux systems the route is created automatically on the client-side. For the target-side
    you can use :py:func:`.add_route_to_plc`.

.. code:: python

    >>> import pyads

    >>> # create some constants for connection
    >>> CLIENT_NETID = "192.168.1.10.1.1"  # The desired Ams Net Id of this device, choose freely
    >>> CLIENT_IP = "192.168.1.10"  # The IP address of this device
    >>> TARGET_IP = "192.168.1.11"  # The IP address of the target (most likely a PLC)
    >>> TARGET_USERNAME = "Administrator"  # Standard Beckhoff user name
    >>> TARGET_PASSWORD = "1"  # Standard Beckhoff password
    >>> ROUTE_NAME = "route-to-my-plc"  # A suitable description of the route
    >>> TARGET_NETID = "5.83.131.116.1.1" # The Ams Net Id of the target device. In TwinCAT3 created from device MAC address by default

    >>> # add a new route to the target plc
    >>> pyads.add_route_to_plc(
    >>>     CLIENT_NETID, CLIENT_IP, TARGET_IP, TARGET_USERNAME, TARGET_PASSWORD,
    >>>     route_name=ROUTE_NAME
    >>> )

    >>> # connect to plc and open connection
    >>> # route is added automatically to client on Linux, on Windows use the TwinCAT router
    >>> plc = pyads.Connection(TARGET_NETID, pyads.PORT_TC3PLC1)
    >>> plc.open()

    >>> # check the connection state
    >>> plc.read_state()
    (0, 5)

    >>> # read int value by name
    >>> i = plc.read_by_name("GVL.int_val")

    >>> # write int value by name
    >>> plc.write_by_name("GVL.real_val", 42.0)

    >>> # create a symbol that automatically updates to the plc value
    >>> real_val = plc.get_symbol("GVL.real_val", auto_update=True)
    >>> print(real_val.value)
    42.0
    >>> real_val.value = 5.0
    >>> print(plc.read_by_name("GVL.real_val"))
    5.0

    >>> # close connection
    >>> plc.close()
