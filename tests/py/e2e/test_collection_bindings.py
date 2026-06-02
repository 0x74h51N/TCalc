import calc_native


def test_collection_kind_exposed():
    assert calc_native.CollectionKind.List is not None
    assert calc_native.CollectionKind.Point is not None


def test_tokenize_list_yields_collection_token():
    branch = calc_native.tokenize_string("[1,2,3]")
    assert len(branch.tokens) == 1
    tok = branch.tokens[0]
    assert tok.kind == calc_native.TokenKind.Collection
    col = tok.as_collection()
    assert col.kind == calc_native.CollectionKind.List
    assert col.closed is True
    assert len(col.elements) == 3


def test_tokenize_point_yields_collection_token():
    branch = calc_native.tokenize_string("(1,2)")
    col = branch.tokens[0].as_collection()
    assert col.kind == calc_native.CollectionKind.Point
    assert len(col.elements) == 2


def test_collection_indices_populated():
    branch = calc_native.tokenize_string("1 + [2,3]")
    assert list(branch.collection_indices) == [2]


def test_unclosed_collection_flag():
    branch = calc_native.tokenize_string("[1,2,3")
    col = branch.tokens[0].as_collection()
    assert col.closed is False
    assert len(col.elements) == 3
