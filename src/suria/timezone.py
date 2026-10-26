"""Timezone helpers for solar sites."""


def get_timezone(lat: float, lon: float, tz: str = None) -> str:
    """Return a timezone string for a lat/lon pair.

    If ``tz`` is provided explicitly, it is returned unchanged.
    Otherwise a longitude-based approximation is used:

        offset_hours = round(lon / 15)
        return f"Etc/GMT-{offset_hours}"

    Note: ``Etc/GMT-N`` means UTC+N (the sign is inverted per IANA).
    """
    if tz:
        return tz
    offset = round(lon / 15)
    # Etc/GMT sign convention is inverted: Etc/GMT-8 == UTC+8
    # Using {-offset} so positive lon → negative suffix (UTC+), negative lon → positive suffix (UTC-)
    return f"Etc/GMT{-offset:+d}"
