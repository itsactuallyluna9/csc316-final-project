import click

@click.group()
def cli() -> None:
    """Entry point for the csc316_final_project package."""
    pass

@cli.command()
def train():
    pass

def test():
    pass

if __name__ == "__main__":
    cli()
