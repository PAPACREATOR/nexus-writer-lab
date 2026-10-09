"""Offline, bounded source-prototype checks only; no Writer execution."""
import pytest
from lab.patch_lpac_pipe_source import PROTOTYPE, SOURCE_TOKEN, patch_source


BASE = (
    "/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */\n"
    '#define PIPESYSTEM      "\\\\\\\\.\\\\pipe\\\\"\n'
    '#define PIPEPREFIX      "OSL_PIPE_"\n'
    "void osl_createPipe() {\n"
    + SOURCE_TOKEN + "\n"
    "    CreateNamedPipeW(path);\n"
    "    WaitNamedPipeW(path);\n"
    "}\n"
)


def test_source_prototype_selects_local_only_for_self_appcontainer():
    out = patch_source(BASE)
    assert out != BASE
    assert out.count("GetTokenInformation(") == 1
    assert out.count("TokenIsAppContainer") == 1
    assert out.count("OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY") == 1
    assert out.count("CloseHandle(nexusPipeSelfToken)") == 1
    assert out.count(SOURCE_TOKEN) == 1
    assert "&& nexusAppContainer != 0" in out
    assert "LOCAL" in out
    assert "CreateNamedPipeW(path)" in out
    assert "WaitNamedPipeW(path)" in out
    assert "#define PIPESYSTEM" in out
    assert "SetNamedSecurityInfo" not in out
    assert "SetSecurityInfo" not in out
    assert "ConvertStringSecurityDescriptor" not in out
    assert "SetSecurityDescriptorDacl" not in out
    assert "AdjustTokenPrivileges" not in out
    assert "CreateProcess" not in out


@pytest.mark.parametrize("source", [
    "",
    "unexpected",
    BASE.replace(SOURCE_TOKEN, ""),
    BASE.replace(SOURCE_TOKEN, SOURCE_TOKEN + SOURCE_TOKEN),
    BASE.replace("WaitNamedPipeW(", "WaitPipe("),
    BASE.replace("CreateNamedPipeW(", "CreatePipe("),
    BASE.replace("#define PIPESYSTEM", "#define ANOTHER"),
    BASE + "nexusPipeSelfToken",
])
def test_source_mismatch_rejected_without_fallback(source):
    with pytest.raises(ValueError):
        patch_source(source)


def test_prototype_has_no_implicit_action_or_broad_grant():
    assert "LOCAL" in PROTOTYPE
    assert "GetCurrentProcess" in PROTOTYPE
    assert "GetTokenInformation" in PROTOTYPE
    assert "OpenProcessToken" in PROTOTYPE
    assert "CloseHandle" in PROTOTYPE
    assert "CreateNamedPipeW" not in PROTOTYPE
    assert "Everyone" not in PROTOTYPE
    assert "FullControl" not in PROTOTYPE
    assert "DACL" in PROTOTYPE
