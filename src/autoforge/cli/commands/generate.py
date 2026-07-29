import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def generate() -> None:
    """프로젝트 생성 명령의 현재 구현 상태를 알린다."""
    typer.echo(
        "generate 명령은 Workspace 적용 단계 이후 제공됩니다.",
        err=True,
    )
    raise typer.Exit(code=1)
