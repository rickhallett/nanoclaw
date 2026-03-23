"""jobctl — job hunting CLI for the halos ecosystem."""

import click

from jobctl.commands.seed import seed_cmd
from jobctl.commands.list_cmd import list_cmd
from jobctl.commands.show import show_cmd
from jobctl.commands.review import review_cmd
from jobctl.commands.apply import apply_cmd
from jobctl.commands.status import status_cmd
from jobctl.commands.metrics import metrics_cmd


@click.group()
@click.version_option(version="0.1.0", prog_name="jobctl")
def main():
    """jobctl — job hunting CLI for the halos ecosystem.

    Track job applications, generate tailored cover letters,
    and monitor the pipeline from discovery to offer.
    """
    pass


main.add_command(seed_cmd, name="seed")
main.add_command(list_cmd, name="list")
main.add_command(show_cmd, name="show")
main.add_command(review_cmd, name="review")
main.add_command(apply_cmd, name="apply")
main.add_command(status_cmd, name="status")
main.add_command(metrics_cmd, name="metrics")
