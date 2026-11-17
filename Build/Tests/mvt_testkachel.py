# Minimaler MVT-Encoder fuer Tests: eine Ebene "f" mit einem Polygon ueber die ganze Kachel
# und eine Ebene "poi" mit Punkten (class/subclass/rank/name).
def _varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); return bytes(out)
def _key(field, wt): return _varint((field << 3) | wt)
def _ld(field, data): return _key(field, 2) + _varint(len(data)) + data
def _zz(n): return (n << 1) ^ (n >> 31)
def _value_str(s): return _ld(1, s.encode())
def _value_int(i): return _key(4, 0) + _varint(i)
def layer(name, features, extent=4096):
    keys, vals, kidx, vidx, body = [], [], {}, {}, b""
    for geomtype, geom, props in features:
        tags = []
        for k, v in props.items():
            if k not in kidx: kidx[k] = len(keys); keys.append(k)
            vk = (type(v).__name__, v)
            if vk not in vidx:
                vidx[vk] = len(vals); vals.append(_value_str(v) if isinstance(v, str) else _value_int(v))
            tags += [kidx[k], vidx[vk]]
        f = _ld(2, b"".join(_varint(t) for t in tags)) + _key(3, 0) + _varint(geomtype) + _ld(4, b"".join(_varint(g) for g in geom))
        body += _ld(2, f)
    out = _key(15, 0) + _varint(2) + _ld(1, name.encode()) + body
    for k in keys: out += _ld(3, k.encode())
    for v in vals: out += _ld(4, v)
    out += _key(5, 0) + _varint(extent)
    return _ld(3, out)
def polygon_full(extent=4096, inset=40):
    a, b = inset, extent - inset
    return [(1 << 3) | 1, _zz(a), _zz(a), (3 << 3) | 2, _zz(b - a), _zz(0), _zz(0), _zz(b - a), _zz(a - b), _zz(0), 15]
def point(x, y): return [(1 << 3) | 1, _zz(x), _zz(y)]
def tile(pois):
    feats = [(1, point(x, y), props) for (x, y, props) in pois]
    return layer("f", [(3, polygon_full(), {"k": "v"})]) + layer("poi", feats)
