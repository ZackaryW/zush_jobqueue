from zush_jobqueue.cli import build_cli


def main() -> None:
    build_cli().main(prog_name="zush-jobqueue")
