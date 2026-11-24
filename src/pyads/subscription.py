"""Decoded device-notification subscriptions.

:author: Adam Pasztor
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2026-11-24

"""
from __future__ import annotations

import logging
import threading
from ctypes import Array, sizeof
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Tuple, Type

from .constants import (
    ADST_STRING,
    ADST_WSTRING,
    DATATYPE_MAP,
    PLCTYPE_STRING,
    PLCTYPE_WSTRING,
    ads_type_to_ctype,
)

if TYPE_CHECKING:  # pragma: no cover
    from .connection import Connection

logger = logging.getLogger(__name__)

#: Default ``cycle_time`` (ms) for :meth:`Connection.subscribe`: the PLC checks
#: for a change at most every 100 ms, i.e. at most 10 updates/s per variable.
DEFAULT_CYCLE_TIME_MS: float = 100.0

#: Default ``max_delay`` (ms) for :meth:`Connection.subscribe`.
DEFAULT_MAX_DELAY_MS: float = 0.0


@dataclass(frozen=True)
class Notification:
    """A decoded device notification, as passed to a subscription callback.

    :ivar name: variable name as subscribed
    :ivar value: decoded Python value
    :ivar timestamp: PLC timestamp of the change (timezone-aware, UTC)
    :ivar handle: ADS notification handle

    """

    name: str
    value: Any
    timestamp: datetime
    handle: int


def _unresolvable(name: str, symbol_type: str, reason: str) -> TypeError:
    return TypeError(
        f"Cannot determine the type of {name!r} ({symbol_type}): {reason}; "
        "pass plc_datatype= explicitly"
    )


def resolve_notification_type(
    name: str,
    symbol_type: str,
    data_type: Optional[int],
    size: Optional[int],
) -> Tuple[Type, int]:
    """Determine the PLC datatype and byte size of a symbol for decoding.

    Uses the textual symbol type for arrays and the numeric ADS base type
    (``dataType``) for everything else, so ENUMs, aliases, subranges and
    ``STRING(n)`` resolve without extra ADS requests. Anything that cannot be
    decoded with confidence raises instead of delivering wrong values.

    :param str name: symbol name (used in error messages)
    :param str symbol_type: PLC type string, e.g. ``"ARRAY [0..9] OF INT"``
    :param data_type: ``ADST_*`` base type code from the symbol entry
    :type data_type: Optional[int]
    :param size: symbol size in bytes from the symbol entry
    :type size: Optional[int]
    :raises TypeError: if the type cannot be resolved
    :return: the PLC datatype and the notification length in bytes
    :rtype: Tuple[Type, int]

    """
    if symbol_type.startswith("ARRAY"):
        # Imported here: symbol.py imports this module.
        from .symbol import AdsSymbol

        try:
            array_type = AdsSymbol.get_type_from_str(symbol_type)
        except (TypeError, ValueError):
            array_type = None
        if (
            array_type is None
            or not issubclass(array_type, Array)
            or array_type._type_ not in DATATYPE_MAP
        ):
            raise _unresolvable(
                name,
                symbol_type,
                "only one-dimensional arrays of base types are decoded automatically",
            )
        if size is not None and sizeof(array_type) != size:
            raise _unresolvable(
                name,
                symbol_type,
                f"size mismatch ({sizeof(array_type)} != {size} bytes)",
            )
        return array_type, sizeof(array_type)

    if data_type in (ADST_STRING, ADST_WSTRING):
        if not size:
            raise _unresolvable(name, symbol_type, "unknown string size")
        return (PLCTYPE_STRING if data_type == ADST_STRING else PLCTYPE_WSTRING), size

    if data_type is not None and data_type in ads_type_to_ctype:
        ctype = ads_type_to_ctype[data_type]
        if size is not None and sizeof(ctype) != size:
            raise _unresolvable(
                name, symbol_type, f"size mismatch ({sizeof(ctype)} != {size} bytes)"
            )
        return ctype, sizeof(ctype)

    raise _unresolvable(
        name, symbol_type, "structures and other complex types are not decoded automatically"
    )


class Subscription:
    """A live, decoded device notification created by ``subscribe()``.

    Returned by :meth:`pyads.Connection.subscribe` and
    :meth:`pyads.AdsSymbol.subscribe`. It stays active until
    :meth:`unsubscribe` is called or the connection is closed; dropping the
    Python object does **not** end it. Can be used as a context manager.

    :ivar name: variable name as subscribed
    :ivar plc_datatype: PLC datatype used for decoding
    :ivar size: notification length in bytes
    :ivar notification_handle: ADS notification handle (set once registered)
    :ivar user_handle: user handle returned by the registration

    """

    def __init__(
        self, connection: "Connection", name: str, plc_datatype: Type, size: int
    ) -> None:
        """Create an unregistered subscription (internal; use ``subscribe()``)."""
        self._connection = connection
        self.name = name
        self.plc_datatype = plc_datatype
        self.size = size
        self.notification_handle: Optional[int] = None
        self.user_handle: Optional[int] = None
        self._lock = threading.Lock()
        self._active = True
        self._error_count = 0

    def __repr__(self) -> str:
        """Return a short description of the subscription."""
        state = "active" if self._active else "inactive"
        return f"<Subscription {self.name!r} handle={self.notification_handle} {state}>"

    @property
    def active(self) -> bool:
        """Return True while the subscription delivers notifications.

        :rtype: bool

        """
        return self._active

    def unsubscribe(self) -> None:
        """Remove the device notification. Calling it again is a no-op.

        :raises ADSError: if the PLC rejects the removal (the subscription is
            inactive locally regardless)

        """
        with self._lock:
            if not self._active:
                return
            self._active = False
        self._connection._remove_subscription(self)

    def __enter__(self) -> "Subscription":
        """Return the subscription itself."""
        return self

    def __exit__(self, *exc: Any) -> None:
        """Unsubscribe on leaving the with-block."""
        self.unsubscribe()

    def _report_error(self) -> None:
        """Log an exception from decoding or the user callback.

        Must be called from inside an ``except`` block. The first error of a
        subscription is logged with traceback at ERROR level, later ones only
        at DEBUG so a broken callback on a fast variable cannot flood the log.
        """
        self._error_count += 1
        if self._error_count == 1:
            logger.exception(
                "Error handling notification for %s (further errors logged at DEBUG)",
                self.name,
            )
        else:
            logger.debug(
                "Error handling notification for %s (%d errors)",
                self.name,
                self._error_count,
                exc_info=True,
            )
