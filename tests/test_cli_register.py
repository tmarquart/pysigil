from pysigil import cli

def test_register_alias_parses_to_setup() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(["register"])
    assert ns.func is cli.setup_cmd
