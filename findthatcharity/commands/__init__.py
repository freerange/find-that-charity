import click

from .indexdata import cli as index_cli
from .createexport import cli as export_cli

cli = click.CommandCollection(sources=[index_cli, export_cli])