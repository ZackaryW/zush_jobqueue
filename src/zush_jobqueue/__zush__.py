from zush.plugin import Plugin

from zush_jobqueue.cli import build_cli


ZushPlugin = Plugin()
ZushPlugin.commands["jobqueue"] = build_cli(include_serve=False)