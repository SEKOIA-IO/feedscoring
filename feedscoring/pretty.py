from rich.progress import BarColumn, Progress, TextColumn


def print_score(name: str, value: int, max_value: int, depth: int = 1) -> None:
    """
    Print a graphical histogram-style bar
    """
    progress = Progress(
        TextColumn(" " * depth * 4 + f"[bold blue]{name}:"),
        BarColumn(
            bar_width=70 - depth * 4 - len(name),
            complete_style="green",
            finished_style="bold green",
        ),
        TextColumn(f"[green]{value:0.1f}/{max_value:0d}"),
    )

    with progress:
        progress.add_task("progress", total=max_value, completed=value)


def print_scores(scores: dict, depth: int = 0):
    """
    Print scores in a nested fashion
    """
    if depth == 0:
        print()
    n = 0
    for k, v in scores.items():
        if isinstance(v, dict):
            print(f"{'  ' * depth * 4}{k}:")
            n += print_scores(v, depth + 1) + 1
        else:
            print_score(k, v, 100, depth)
            n += 1
    return n
