"""GeoJSON documents for the areas drawn on the map.

Every GeoJSON literal in the application is built here, so the shape of the
representation lives in one place instead of being spelled out at each call
site. Callers hand over plain coordinates; how many levels of nesting that
takes is this module's business.

On the nesting: ``polygon`` writes a bare ring (depth 2) rather than the
RFC 7946 list-of-rings (depth 3), and ``multiPolygon`` writes a list of rings
(depth 3) rather than a list of polygons (depth 4). That deviation is the
convention the rest of the repository reads and writes today. Removing it is
target B in ``docs/geojson-refactor-plan.md``; when it lands, only this module
changes and no call site does.
"""


def point(coordinate):
    """A single ``(lon, lat)`` position, normalised to a list."""
    return {'type': 'Point', 'coordinates': list(coordinate)}


def lineString(points):
    """An open path through ``points``."""
    return {'type': 'LineString', 'coordinates': list(points)}


def polygon(ring):
    """A closed area from a single ``ring`` of positions."""
    return {'type': 'Polygon', 'coordinates': list(ring)}


def multiPolygon(rings):
    """Several disjoint areas, one ``ring`` each."""
    return {'type': 'MultiPolygon', 'coordinates': [list(ring) for ring in rings]}


def feature(geometry=None, **properties):
    """A geometry plus the properties the map reads.

    ``geometry`` is left out of the document when it is ``None``, which is how
    the parsers say that a location has no drawable area yet.
    """
    document = {'type': 'Feature', 'properties': properties}
    if geometry is not None:
        document['geometry'] = geometry
    return document


def featureCollection(features):
    return {'type': 'FeatureCollection', 'features': list(features)}


def geometryCollection(geometries):
    return {'type': 'GeometryCollection', 'geometries': list(geometries)}


def hasGeometry(feature):
    """Whether a feature -- or the ``None`` the parsers return -- draws."""
    return bool(feature) and 'geometry' in feature
