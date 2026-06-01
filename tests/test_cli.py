from open_idotmatrix.cli import build_parser


def test_gif_parser_accepts_ack_policy_and_gatt_chunk_size():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--address",
            "AA:BB",
            "--gatt-chunk-size",
            "244",
            "gif",
            "demo.gif",
            "--ack-policy",
            "ok_or_done",
        ]
    )

    assert args.command == "gif"
    assert args.gatt_chunk_size == 244
    assert args.ack_policy == "ok_or_done"


def test_smoke_test_parser_has_safe_defaults():
    parser = build_parser()
    args = parser.parse_args(["--address", "AA:BB", "smoke-test", "--out", "out/check.json", "--skip-gif"])

    assert args.command == "smoke-test"
    assert args.out == "out/check.json"
    assert args.skip_gif is True
    assert args.no_ack is False
