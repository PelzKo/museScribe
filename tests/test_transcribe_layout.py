from omrbench.transcribe import staff_order


def test_staff_order_follows_list_and_keeps_unknown_parts_with_their_file():
    labels = ["Violine 1", "Flöte 1", "Klarinette in B 1", "Others", "Frauen", "All"]
    files = [0, 1, 1, 2, 2, 2]
    order = ["Frauen", "Flöte 1", "Klarinette in B 1", "Violine 1"]
    # "Others" (unknown, first in its file) stays with Frauen; "All" after Frauen
    assert [labels[i] for i in staff_order(labels, files, order)] == \
        ["Others", "Frauen", "All", "Flöte 1", "Klarinette in B 1", "Violine 1"]
    assert staff_order(labels, files, []) == list(range(6))


def test_written_c_key_added_to_transposing_staff(tmp_path):
    import zipfile
    from omrbench.transcribe import written_c_keys
    part = ("<Part id=\"{i}\">\n      <Staff>\n        </Staff>\n      <Instrument>{t}</Instrument>\n    </Part>")
    staff = ('<Staff id="{i}">\n      <Measure>\n        <voice>\n          <Clef>\n            </Clef>\n'
             '          {k}<Rest/>\n          </voice>\n        </Measure>\n      </Staff>')
    mscx = (part.format(i=1, t="") + part.format(i=2, t="<transposeChromatic>-2</transposeChromatic>")
            + part.format(i=3, t="<transposeChromatic>-7</transposeChromatic>")
            + staff.format(i=1, k="") + staff.format(i=2, k="") + staff.format(i=3, k="<KeySig/>"))
    f = tmp_path / "x.mscz"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("x.mscx", mscx)
    assert written_c_keys(f) == 1          # Bb clarinet without a key; the horn has one, the violin is in C
    text = zipfile.ZipFile(f).read("x.mscx").decode()
    assert "<concertKey>-2</concertKey>" in text and text.count("<KeySig") == 2
