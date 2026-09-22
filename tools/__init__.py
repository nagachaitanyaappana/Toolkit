from __future__ import annotations

from typing import Protocol


class Tool(Protocol):
    """Standard interface that every toolkit tool must implement."""

    name: str
    description: str
    icon: str

    def run(self) -> None:
        """Execute the tool's main logic."""
        ...


# Registry: list of (name, description, icon, factory) tuples.
# Tools are added by importing them in the tool_modules list below.
_tool_registry: list[Tool] = []


def register_tool(tool: Tool) -> None:
    """Register a tool instance so it appears in the main menu."""
    _tool_registry.append(tool)


def get_all_tools() -> list[Tool]:
    """Return the list of registered tools (lazy-loaded)."""
    if not _tool_registry:
        _load_tools()
    return _tool_registry


def _load_tools() -> None:
    """Import and instantiate all tool modules, registering each one."""
    from tools.downloader import DownloaderTool
    from tools.message_sender import MessageSenderTool
    from tools.phone_checker import PhoneCheckerTool
    from tools.qr_generator import QRGeneratorTool
    from tools.password_mgr import PasswordManagerTool
    from tools.sysinfo import SysInfoTool

    # Instantiate and register each tool
    register_tool(DownloaderTool())
    register_tool(MessageSenderTool())
    register_tool(PhoneCheckerTool())
    register_tool(QRGeneratorTool())
    register_tool(PasswordManagerTool())
    register_tool(SysInfoTool())