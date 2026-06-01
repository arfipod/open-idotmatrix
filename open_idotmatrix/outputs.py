"""Frame outputs for simulator, hardware, and combined rendering."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from .framebuffer import MatrixFrame
from .renderer import MatrixRenderer
from .simulator import MatrixSimulator


class FrameOutput(Protocol):
    async def show(self, frame: MatrixFrame) -> Any:
        """Render one frame."""


class SimulatorOutput:
    """Render frames into a MatrixSimulator and optionally save/show previews."""

    def __init__(
        self,
        simulator: MatrixSimulator | None = None,
        *,
        save_path: str | Path | None = None,
        scale: int = 16,
        grid: bool = True,
        window: bool = False,
    ) -> None:
        self.simulator = simulator or MatrixSimulator()
        self.save_path = Path(save_path) if save_path is not None else None
        self.scale = scale
        self.grid = grid
        self.window = window

    async def show(self, frame: MatrixFrame) -> dict[str, Any]:
        self.simulator.from_frame(frame)
        saved: str | None = None
        if self.save_path is not None:
            saved = str(self.simulator.save(self.save_path, scale=self.scale, grid=self.grid))
        if self.window:
            self.simulator.show(scale=self.scale, grid=self.grid)
        return {"output": "simulator", "saved": saved}


class HardwareOutput:
    """Render frames to a connected OpenIDotMatrix device through MatrixRenderer."""

    def __init__(self, device: Any, **renderer_kwargs: Any) -> None:
        self.device = device
        self.renderer = MatrixRenderer(device, **renderer_kwargs)

    async def show(self, frame: MatrixFrame) -> dict[str, Any]:
        result = await self.renderer.show(frame)
        return {"output": "hardware", "result": result}


class TeeOutput:
    """Send each frame to several outputs, for example simulator and hardware."""

    def __init__(self, *outputs: FrameOutput) -> None:
        self.outputs = list(outputs)

    async def show(self, frame: MatrixFrame) -> list[Any]:
        results = []
        for output in self.outputs:
            results.append(await output.show(frame))
        return results

    @classmethod
    def from_sequence(cls, outputs: Sequence[FrameOutput]) -> TeeOutput:
        return cls(*outputs)


__all__ = ["FrameOutput", "HardwareOutput", "SimulatorOutput", "TeeOutput"]
