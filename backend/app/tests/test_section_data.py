import pytest

from app.models.section import SectionDataRequest
from app.parsers.plt_parser import ParsedPlt, parse_plt_text
from app.services.section_data import SectionDataError, extract_section_data
from app.tests.sample_data import DX, Z_LEVELS, make_plt_text, temp_value

NI, NJ, NK = 4, 5, 3


@pytest.fixture
def entry() -> ParsedPlt:
    return parse_plt_text(make_plt_text(NI, NJ, NK))


def request(plane: str, slice_index: int, variable: str = "TEMP", include_vectors: bool = True) -> SectionDataRequest:
    return SectionDataRequest(
        file_id="dummy", plane=plane, slice_index=slice_index, variable=variable, include_vectors=include_vectors
    )


@pytest.mark.parametrize(
    ("plane", "slice_index", "h_label", "v_label", "h_len", "v_len", "actual_coord"),
    [
        ("XY", 1, "X", "Y", NI, NJ, Z_LEVELS[1]),
        ("XZ", 2, "X", "Z", NI, NK, 2 * DX),
        ("YZ", 3, "Y", "Z", NJ, NK, 3 * DX),
    ],
)
def test_extract_shapes_axes_and_slice_coord(entry, plane, slice_index, h_label, v_label, h_len, v_len, actual_coord):
    res = extract_section_data(entry, request(plane, slice_index))

    assert (res.h_label, res.v_label) == (h_label, v_label)
    assert len(res.h_coords) == h_len
    assert len(res.v_coords) == v_len
    assert len(res.values) == v_len
    assert all(len(row) == h_len for row in res.values)
    assert res.actual_coord == pytest.approx(actual_coord)
    assert res.actual_index == slice_index


def test_extract_values_match_source_grid(entry):
    # XZ 断面 (j=2 固定): values[k][i] が TEMP(i, 2, k) と一致すること
    res = extract_section_data(entry, request("XZ", 2))
    for k in range(NK):
        for i in range(1, NI):
            assert res.values[k][i] == pytest.approx(temp_value(i, 2, k))


def test_missing_values_become_none_and_are_excluded_from_range(entry):
    res = extract_section_data(entry, request("XY", 0))

    # i=0 の列は陸地（-999）なので None
    assert all(row[0] is None for row in res.values)
    assert all(v is not None for row in res.values for v in row[1:])

    expected = [temp_value(i, j, 0) for j in range(NJ) for i in range(1, NI)]
    assert res.value_range == pytest.approx([min(expected), max(expected)])


def test_vectors_follow_plane_components(entry):
    res = extract_section_data(entry, request("YZ", 2))
    assert (res.vector_h_label, res.vector_v_label) == ("V", "W")
    assert res.vector_h[1][3] == pytest.approx(0.05 * 3)  # V = 0.05*j
    assert res.vector_v[1][3] == pytest.approx(0.01 * 1)  # W = 0.01*k


def test_vectors_masked_on_land(entry):
    res = extract_section_data(entry, request("XY", 0))
    assert all(row[0] is None for row in res.vector_h)
    assert all(row[0] is None for row in res.vector_v)


def test_vectors_omitted_when_not_requested(entry):
    res = extract_section_data(entry, request("XY", 0, include_vectors=False))
    assert res.vector_h is None and res.vector_v is None


@pytest.mark.parametrize(("plane", "bad_index"), [("XY", NK), ("XZ", -1), ("YZ", NI)])
def test_slice_index_out_of_range(entry, plane, bad_index):
    with pytest.raises(SectionDataError, match="slice_index"):
        extract_section_data(entry, request(plane, bad_index))


def test_unknown_variable(entry):
    with pytest.raises(SectionDataError, match="NOPE"):
        extract_section_data(entry, request("XY", 0, variable="NOPE"))


def test_all_missing_section_is_an_error(entry):
    # YZ 断面 i=0 は全点が陸地
    with pytest.raises(SectionDataError, match="有効なデータ"):
        extract_section_data(entry, request("YZ", 0))
