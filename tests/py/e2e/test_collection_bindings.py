import calc_native


def test_collection_kind_exposed():
    assert calc_native.Collection.Kind.List is not None
    assert calc_native.Collection.Kind.Point is not None


def test_tokenize_list_yields_collection_token():
    branch = calc_native.tokenize_string("[1,2,3]")
    assert len(branch.tokens) == 1
    tok = branch.tokens[0]
    assert tok.kind == calc_native.TokenKind.Paren
    par = tok.as_paren()
    # ParenToken carries paren-char kind (Bracket for '[]'); the eval layer
    # maps Bracket → Collection.Kind.List when constructing a Collection.
    assert par.kind == calc_native.ParenKind.Bracket
    assert par.has_close is True
    assert len(par.elements) == 3


def test_tokenize_point_yields_collection_token():
    branch = calc_native.tokenize_string("(1,2)")
    par = branch.tokens[0].as_paren()
    assert par.kind == calc_native.ParenKind.Paren  # eval maps to Point
    assert len(par.elements) == 2


def test_collection_indices_populated():
    branch = calc_native.tokenize_string("1 + [2,3]")
    assert list(branch.paren_indices) == [2]


def test_unclosed_collection_flag():
    branch = calc_native.tokenize_string("[1,2,3")
    col = branch.tokens[0].as_paren()
    assert col.has_close is False
    assert len(col.elements) == 3


def test_collection_elements_mixed_variant_surface():
    branch = calc_native.tokenize_string("[1, +2, 3+4]")
    col = branch.tokens[0].as_paren()
    assert len(col.elements) == 3
    # element 0: single NumberToken Token instance
    assert isinstance(col.elements[0], calc_native.Token)
    assert col.elements[0].kind == calc_native.TokenKind.Number
    # element 1: [Op(UnaryPlus), NumberToken] list of Token
    assert isinstance(col.elements[1], list)
    assert len(col.elements[1]) == 2
    # element 2: [N, Op, N] list of Token
    assert isinstance(col.elements[2], list)
    assert len(col.elements[2]) == 3


def test_collection_rows_uniform_list_of_lists():
    branch = calc_native.tokenize_string("[1, +2, 3+4]")
    col = branch.tokens[0].as_paren()
    rows = col.rows()
    assert isinstance(rows, list)
    assert len(rows) == 3
    for row in rows:
        assert isinstance(row, list)
        for tok in row:
            assert isinstance(tok, calc_native.Token)
    # row 0 wraps the single Number into a one-element list
    assert len(rows[0]) == 1
    assert rows[0][0].kind == calc_native.TokenKind.Number
    # row 1 preserves the two token sequence
    assert len(rows[1]) == 2
    # row 2 preserves the three token expression
    assert len(rows[2]) == 3
