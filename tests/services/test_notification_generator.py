import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    NotificationSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.notification import NotificationGenerator


def specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(
            notification=NotificationSpec(
                enabled=enabled,
                webhook_url_environment="KIS_NOTIFICATION_WEBHOOK_URL",
            )
        ),
    )


def test_notification_generator_is_empty_until_enabled() -> None:
    assert NotificationGenerator().render(specification()) == {}


def test_notification_generator_renders_generated_runtime_contract() -> None:
    files = NotificationGenerator().render(specification(enabled=True))
    root = PurePosixPath(
        "src", "kis_auto_trading", "infrastructure", "notification"
    )

    assert set(files) == {
        root / "__init__.py",
        root / "config.py",
        root / "fake.py",
        root / "protocol.py",
        root / "service.py",
        root / "webhook.py",
    }
    assert "KIS_NOTIFICATION_WEBHOOK_URL" in files[root / "config.py"]
    assert "class Notification:" in files[root / "protocol.py"]
    assert "class FakeNotificationDelivery:" in files[root / "fake.py"]
    assert "class WebhookNotificationDelivery:" in files[root / "webhook.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_notification_plan_marks_runtime_contract_generated() -> None:
    plan = NotificationGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 6
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {
        "project:kis_auto_trading:notification"
    }


def test_notification_makes_httpx_a_runtime_dependency() -> None:
    files = FastAPIProjectGenerator().render(specification(enabled=True))
    runtime_dependencies, _ = files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )

    assert '    "httpx>=0.28,<1",' in runtime_dependencies


@pytest.mark.anyio
async def test_generated_notification_dispatcher_uses_webhook_without_retry_policy(
    tmp_path: Path,
) -> None:
    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)

    for job_id, generator in [
        ("project-job", FastAPIProjectGenerator()),
        ("notification-job", NotificationGenerator()),
    ]:
        rendered = generator.render(specification_value)
        plan = GenerationPlanResolver().resolve(
            generator.plan(specification_value), workspace
        )
        GenerationPlanApplier().apply(
            job_id=job_id,
            plan=plan,
            rendered_files=rendered,
            workspace=workspace,
        )

    code = (
        "import asyncio\n"
        "import json\n"
        "import sys\n"
        "import httpx\n"
        "sys.path.insert(0, 'src')\n"
        "from kis_auto_trading.infrastructure.notification import (\n"
        "    Notification, NotificationConfig, NotificationDeliveryError,\n"
        "    NotificationDispatcher, WebhookNotificationDelivery,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    requests = []\n"
        "    async def accepted(request):\n"
        "        requests.append(request)\n"
        "        return httpx.Response(202, request=request)\n"
        "    client = httpx.AsyncClient(transport=httpx.MockTransport(accepted))\n"
        "    delivery = WebhookNotificationDelivery(\n"
        "        NotificationConfig('https://notify.test/hook'), client=client\n"
        "    )\n"
        "    dispatcher = NotificationDispatcher(delivery)\n"
        "    await dispatcher.send(Notification('Trade filled', '005930', {'order_id': '42'}))\n"
        "    assert len(requests) == 1\n"
        "    assert json.loads(requests[0].content) == {\n"
        "        'subject': 'Trade filled', 'body': '005930',\n"
        "        'attributes': {'order_id': '42'},\n"
        "    }\n"
        "    await dispatcher.aclose()\n"
        "    assert not client.is_closed\n"
        "    await client.aclose()\n"
        "\n"
        "    async def rejected(request):\n"
        "        return httpx.Response(503, request=request)\n"
        "    failed_client = httpx.AsyncClient(transport=httpx.MockTransport(rejected))\n"
        "    failed_delivery = WebhookNotificationDelivery(\n"
        "        NotificationConfig('https://notify.test/hook'), client=failed_client\n"
        "    )\n"
        "    try:\n"
        "        await failed_delivery.send(Notification('Failure', 'no retry'))\n"
        "    except NotificationDeliveryError:\n"
        "        pass\n"
        "    else:\n"
        "        raise AssertionError('rejected webhook was accepted')\n"
        "    await failed_client.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr
