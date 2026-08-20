import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    EmailSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.email import EmailGenerator
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator


def specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(spec_version="1", project=ProjectInfo(name="KIS", package_name="kis_auto_trading", version="0.1.0"), application=ApplicationSpec(), tooling=ToolingSpec(email=EmailSpec(enabled=enabled, sender_environment="KIS_SMTP_SENDER")))


def test_email_generator_is_empty_until_enabled() -> None:
    assert EmailGenerator().render(specification()) == {}


def test_email_generator_renders_generated_runtime_contract() -> None:
    files = EmailGenerator().render(specification(enabled=True))
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "email")
    assert set(files) == {root / "__init__.py", root / "config.py", root / "fake.py", root / "protocol.py", root / "service.py", root / "smtp.py"}
    assert "KIS_SMTP_SENDER" in files[root / "config.py"]
    assert "class SmtpEmailDelivery:" in files[root / "smtp.py"]
    for path, source in files.items(): ast.parse(source, filename=path.as_posix())


@pytest.mark.anyio
async def test_generated_smtp_email_uses_stdlib_transport(tmp_path: Path) -> None:
    value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    for job_id, generator in [("project", FastAPIProjectGenerator()), ("email", EmailGenerator())]:
        rendered = generator.render(value)
        GenerationPlanApplier().apply(job_id=job_id, plan=GenerationPlanResolver().resolve(generator.plan(value), workspace), rendered_files=rendered, workspace=workspace)
    code = """import asyncio, smtplib, sys
sys.path.insert(0, 'src')
from kis_auto_trading.infrastructure.email import EmailConfig, EmailMessage, SmtpEmailDelivery
sent = []
class Client:
    def __init__(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def starttls(self, **kwargs): pass
    def login(self, username, password): assert (username, password) == ('user', 'secret')
    def send_message(self, message): sent.append(message)
smtplib.SMTP = Client
async def verify():
    delivery = SmtpEmailDelivery(EmailConfig('smtp.test', 587, 'sender@test', 'user', 'secret'))
    await delivery.send(EmailMessage(('to@test',), 'subject', 'body'))
    assert sent[0]['To'] == 'to@test'
asyncio.run(verify())
"""
    result = await AsyncioProcessRunner().run((sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10)
    assert result.succeeded, result.stderr
