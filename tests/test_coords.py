from factorio_trace.coords import WindowBounds, normalize_mouse


BOUNDS = WindowBounds(x=100, y=50, width=800, height=600)


def test_inside_window():
    assert normalize_mouse(100, 50, BOUNDS) == (0.0, 0.0)
    assert normalize_mouse(500, 350, BOUNDS) == (0.5, 0.5)
    assert normalize_mouse(900, 650, BOUNDS) == (1.0, 1.0)


def test_outside_window_dropped():
    assert normalize_mouse(90, 50, BOUNDS) is None
    assert normalize_mouse(100, 40, BOUNDS) is None
    assert normalize_mouse(910, 350, BOUNDS) is None
