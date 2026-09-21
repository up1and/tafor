"""Projections for the SIGMET canvas.

The canvas only ever needs to place a ``(lon, lat)`` on a plane and read it
back, which the two documented projections and the identity do in closed
form. pyproj was pulling in PROJ — 16 MB of the bundle, half of it the EPSG
database — to serve exactly that, so the arithmetic lives here instead.

The three closed forms are all defined on the WGS84 sphere, so no datum
database is involved and no other ellipsoid is served. A configured string
that names something else raises :class:`UnsupportedProjection`: what to
draw instead is a configuration decision, and it is made where the setting
is read rather than here.
"""

import math


class UnsupportedProjection(ValueError):
    """A proj string this module has no closed form for.

    The message carries the reason, so the caller can say why a setting was
    refused without having to re-derive it from the string.
    """


class Projection:
    """Places ``(lon, lat)`` on the canvas plane and reads it back.

    ``geographic`` marks the projections whose plane is still degrees, which
    is what tells the canvas how to scale itself. Subclasses declare the
    ``+proj`` token they serve as ``name``.
    """

    #: the ``+proj`` token this projection serves
    name = ''

    #: whether the plane is still degrees
    geographic = False

    #: WGS84 semi-major axis. Web Mercator (EPSG:3857) and equirectangular
    #: (EPSG:32662) are both defined on the sphere of this radius.
    radius = 6378137.0

    def forward(self, lon, lat):
        """(lon, lat) degrees to plane coordinates."""
        raise NotImplementedError

    def inverse(self, x, y):
        """Plane coordinates to (lon, lat) degrees."""
        raise NotImplementedError

    def __repr__(self):
        return '<{}>'.format(type(self).__name__)


class WebMercator(Projection):
    """The sphere unrolled, y stretched towards the poles."""

    name = 'webmerc'

    def forward(self, lon, lat):
        # asinh(tan) rather than the textbook ln(tan(pi/4 + lat/2)): the two
        # agree to the last bit everywhere except at the equator, where the
        # textbook form returns -7e-10 instead of zero and the canvas would
        # carry a pixel of drift off the origin
        return (self.radius * math.radians(lon),
                self.radius * math.asinh(math.tan(math.radians(lat))))

    def inverse(self, x, y):
        return (math.degrees(x / self.radius),
                math.degrees(math.atan(math.sinh(y / self.radius))))


class Equirectangular(Projection):
    """Degrees scaled by the radius, so x and y keep their degree spacing."""

    name = 'eqc'

    def forward(self, lon, lat):
        return self.radius * math.radians(lon), self.radius * math.radians(lat)

    def inverse(self, x, y):
        return math.degrees(x / self.radius), math.degrees(y / self.radius)


class LongLat(Projection):
    """Geographic coordinates: the plane is still degrees."""

    name = 'longlat'
    geographic = True

    def forward(self, lon, lat):
        return lon, lat

    def inverse(self, x, y):
        return x, y


#: the projections the canvas can place coordinates with, keyed by their
#: ``+proj`` name
projections = {
    'longlat': LongLat,
    'webmerc': WebMercator,
    'eqc': Equirectangular,
}


def split(definition):
    """Split a proj string into its ``+proj`` name and the offset
    parameters it carries.

    An offset parameter would move or reshape the plane, and the closed
    forms are the ones with every one of them at its default, so a string
    carrying one has to be refused rather than silently drawn somewhere
    else.
    """
    offset = ('lon_0', 'lat_0', 'x_0', 'y_0', 'lat_ts', 'k', 'k_0', 'R')

    parameters = {}
    for token in definition.split():
        key, _, value = token.lstrip('+').partition('=')
        parameters[key] = value

    return parameters.get('proj', ''), [key for key in offset if key in parameters]


def proj(definition):
    """Build the projection a proj string names.

    Only the ``+proj`` name is read. Parameters that would move or reshape
    the plane are refused, because the closed forms are the ones with all of
    them at their defaults — ``+datum``, ``+ellps`` and ``+units`` do not
    change the result and are ignored.

    :param definition: str, a proj string as stored in the layer setting
    :return: Projection, the class the name maps to
    :raise UnsupportedProjection: when the string names something else
    """
    name, offset = split(definition) if isinstance(definition, str) else ('', [])

    if name not in projections:
        raise UnsupportedProjection('unknown projection {!r}'.format(name))

    if offset:
        raise UnsupportedProjection('unsupported parameter ' + '/'.join(offset))

    return projections[name]()
