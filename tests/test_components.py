from omrbench import components as C


def test_ola_systems_counts_boxes_inside():
    boxes = [{"cls": "systems", "box": [0, 100, 1000, 300]}, {"cls": "systems", "box": [0, 400, 1000, 600]},
             {"cls": "staves", "box": [0, 110, 1000, 190]}, {"cls": "staves", "box": [0, 210, 1000, 290]},
             {"cls": "staves", "box": [0, 450, 1000, 550]},
             *[{"cls": "system_measures", "box": [i * 250, 100, (i + 1) * 250, 300]} for i in range(4)],
             {"cls": "system_measures", "box": [0, 400, 500, 600]}]
    got = [(s["staves"], s["measures"]) for s in C.ola_systems(boxes)]
    assert got == [(2, 4), (1, 1)]
