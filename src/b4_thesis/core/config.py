"""Configuration management for b4-thesis."""

from pathlib import Path
from typing import Any
import json
from pydantic import BaseModel, Field


class AnalysisConfig(BaseModel):
    """Configuration for analysis settings."""

    output_dir: Path = Field(default=Path("./output"), description="Default output directory")
    default_format: str = Field(default="txt", description="Default output format")
    verbose: bool = Field(default=False, description="Enable verbose logging")
    parallel_jobs: int = Field(default=1, description="Number of parallel jobs")


class VisualizationConfig(BaseModel):
    """Configuration for visualization settings."""

    dpi: int = Field(default=300, description="DPI for saved figures")
    figure_size: tuple[int, int] = Field(default=(10, 6), description="Default figure size")
    style: str = Field(default="whitegrid", description="Seaborn style")
    color_palette: str = Field(default="deep", description="Color palette")


class Config(BaseModel):
    """Main configuration for b4-thesis tool."""

    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)

    @classmethod
    def load_from_file(cls, config_path: Path) -> "Config":
        """Load configuration from a JSON file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            data = json.load(f)

        return cls(**data)

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to a JSON file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(self.model_dump(), f, indent=2, default=str)

    @classmethod
    def get_default(cls) -> "Config":
        """Get default configuration."""
        return cls()


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from file or return default.

    Args:
        config_path: Path to configuration file. If None, returns default config.

    Returns:
        Config object
    """
    if config_path is None:
        # Try to load from default locations
        default_locations = [
            Path.home() / ".config" / "b4-thesis" / "config.json",
            Path.cwd() / "b4-thesis.json",
        ]

        for location in default_locations:
            if location.exists():
                return Config.load_from_file(location)

        return Config.get_default()

    return Config.load_from_file(config_path)
