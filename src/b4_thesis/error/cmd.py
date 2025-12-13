import functools
from typing import Callable

import click
from rich.console import Console

console = Console()


def handle_command_errors(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}", highlight=False)
            raise click.Abort()
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}", highlight=False)
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Unexpected error:[/red] {e}", highlight=False)
            raise click.Abort()

    return wrapper
