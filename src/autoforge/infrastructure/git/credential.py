import os
import shutil
import stat
import sys
import tempfile
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from autoforge.core.git import GitCredentialReference
from autoforge.core.secret import SecretProvider
from autoforge.core.workspace import Workspace

_HELPER_SOURCE = """import os
import sys

prompt = sys.argv[1].lower() if len(sys.argv) > 1 else ""
name = "AUTOFORGE_GIT_USERNAME" if "username" in prompt else "AUTOFORGE_GIT_PASSWORD"
sys.stdout.write(os.environ[name])
"""


@asynccontextmanager
async def git_credential_environment(
    credential: GitCredentialReference | None,
    *,
    secret_provider: SecretProvider | None,
    workspace: Workspace,
) -> AsyncIterator[Mapping[str, str]]:
    if credential is None:
        yield {}
        return
    if secret_provider is None:
        raise ValueError("Git credential requires a SecretProvider")
    password = await secret_provider.resolve(credential.password)
    helper_root = Path(
        tempfile.mkdtemp(prefix=".git-credential-", dir=workspace.root)
    ).resolve()
    try:
        helper_source = helper_root / "askpass.py"
        helper_source.write_text(_HELPER_SOURCE, encoding="utf-8", newline="\n")
        if os.name == "nt":
            launcher = helper_root / "askpass.cmd"
            launcher.write_text(
                f'@"{sys.executable}" "{helper_source}" %*\r\n',
                encoding="utf-8",
            )
        else:
            launcher = helper_root / "askpass.sh"
            launcher.write_text(
                f'#!/bin/sh\nexec "{sys.executable}" "{helper_source}" "$@"\n',
                encoding="utf-8",
                newline="\n",
            )
            launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)
        yield {
            "GIT_ASKPASS": str(launcher),
            "GIT_ASKPASS_REQUIRE": "force",
            "AUTOFORGE_GIT_USERNAME": credential.username,
            "AUTOFORGE_GIT_PASSWORD": password.reveal(),
        }
    finally:
        shutil.rmtree(helper_root)
