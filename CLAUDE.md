# CLAUDE.md - Claude Code Development Guide

This document contains essential information for developing this project with Claude Code.

## Project Overview

**Project Name**: B4 Thesis - Software Engineering Research Analysis Tool
**Purpose**: Python CLI analysis tool for software engineering research
**Python Version**: 3.10+

## Project Structure

```
b4-thesis/
├── src/b4_thesis/          # Main package
│   ├── cli.py              # CLI entry point (Click-based)
│   ├── commands/           # Subcommand implementations
│   │   ├── analyze.py      # Data/repository analysis command
│   │   ├── stats.py        # Statistical metrics command
│   │   └── visualize.py    # Data visualization command
│   ├── core/               # Core utilities
│   │   ├── config.py       # Pydantic-based config management
│   │   └── revision_manager.py  # Revision data management with validation
│   └── analysis/           # Analysis modules (Phase 1-6 ✓)
│       ├── validation/          # Data validation (Phase 6)
│       │   └── data_validator.py  # CSV data validation
│       ├── tracking/            # Method tracking modules (Phase 6 refactored)
│       │   ├── group_helper.py        # Group-related helper functions
│       │   ├── lifetime_tracker.py    # Lifetime tracking logic
│       │   └── revision_pair_processor.py  # Revision pair processing
│       ├── union_find.py        # Union-Find data structure (Phase 1 ✓)
│       ├── similarity.py        # Similarity calculation (N-gram/LCS) (Phase 1 ✓)
│       ├── matching/            # Method matching modules (Phase 2 ✓)
│       │   └── method_matcher.py    # Method matching
│       ├── group_detector.py    # Group detection (Phase 2 ✓)
│       ├── group_matcher.py     # Group matching (Phase 2 ✓)
│       ├── state_classifier.py  # State classification (Phase 2 ✓)
│       ├── method_tracker.py    # Method tracking facade (Phase 3 ✓, refactored Phase 6)
│       └── clone_group_tracker.py  # Group tracking (Phase 3 ✓)
├── tests/                  # Test code (pytest, 282 tests passing)
│   ├── analysis/           # Analysis module tests
│   ├── core/               # Core module tests
│   ├── commands/           # Command tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test fixtures
├── docs/                   # Detailed design docs
│   └── task_breakdown.md   # Task breakdown & roadmap
├── pyproject.toml          # Project config & dependencies
├── README.md               # User documentation
└── CLAUDE.md               # This file (developer guide)
```

## Tech Stack

### Core Technologies
- **CLI Framework**: Click 8.1+ (command-line building)
- **Output Decoration**: Rich 13.0+ (beautiful terminal output)
- **Config Management**: Pydantic 2.12+ (type-safe config)

### Data Analysis & Scientific Computing
- **pandas**: Data analysis & manipulation
- **numpy**: Numerical computation
- **scipy**: Scientific computing
- **scikit-learn**: Machine learning

### Visualization
- **matplotlib**: Basic plotting
- **seaborn**: Statistical data visualization
- **networkx**: Graph & network analysis

### Development Tools
- **ruff**: Linter & formatter (including import sorting)
- **pytest**: Test framework
- **uv**: Package manager

## Development Workflow

### Setup

```bash
# Install dependencies
uv sync --all-groups

# Install in development mode
uv pip install -e .
```

### Dependency Management (Important)

**Always use `uv add` to add dependencies**

```bash
# Add production dependency
uv add <package-name>

# Add development dependency
uv add --dev <package-name>

# Specify version
uv add <package-name>>=1.0.0

# Remove dependency
uv remove <package-name>

# Update dependencies
uv sync
```

**Examples**:
```bash
# Add GitPython for git repo analysis
uv add gitpython

# Add pytest-cov as dev dependency
uv add --dev pytest-cov
```

**Important**:
- Do NOT use `pip install`
- Run `uv sync` after manually editing `pyproject.toml`
- `uv add` automatically updates `pyproject.toml` and `uv.lock`

### Coding Standards

1. **Format**: Use Ruff (line-length: 100)
2. **Import Order**: Auto-sort enabled (stdlib → third-party → first-party)
3. **Strings**: Use double quotes
4. **Type Hints**: Use wherever possible (Python 3.10+ syntax)

### Code Quality Checks

**Important**: This project uses `uv`, so always prefix commands with `uv run`

```bash
# Lint + auto-fix (including import sorting)
uv run ruff check --fix src/

# Format
uv run ruff format src/

# Run tests
uv run pytest tests/

# Verbose test output
uv run pytest tests/ -v

# Run all together (recommended)
uv run ruff check --fix src/ && uv run ruff format src/ && uv run pytest tests/
```

**Important**:
- ❌ `ruff check src/` → Error (command not found)
- ✅ `uv run ruff check src/` → Correct
- ❌ `pytest tests/` → Error (command not found)
- ✅ `uv run pytest tests/` → Correct

#### CI-Only Tests

Some tests (especially performance tests) take too long to run locally and are only executed in GitHub Actions.

**CI-Only Test Mechanism**:
- Identified by `@pytest.mark.ci` marker
- Automatically skipped locally (no CI env variable)
- Automatically run in GitHub Actions (`CI=true` env variable set)

**Test Execution Examples**:
```bash
# Normal test run (CI-only tests skipped)
uv run pytest tests/

# Run only CI-only tests (force run locally)
uv run pytest -m ci tests/

# Exclude CI-only tests
uv run pytest -m "not ci" tests/

# List all markers
uv run pytest --markers
```

**CI-Only Test Examples**:
- `test_track_all_performance`: Medium dataset (3 revisions) performance test
  - Runtime: ~3 minutes
  - Location: `tests/integration/test_real_data_validation.py`

**Note**: Real data tests (`data/clone_NIL/`) and CI-only tests are independent features:
- Real data absent: All real data tests skipped
- Local environment: CI-only tests skipped (even if real data exists)
- GitHub Actions: CI-only tests run if real data exists

### Adding New Commands

1. Create new file in `src/b4_thesis/commands/` (e.g., `new_command.py`)
2. Define command with Click decorator:
   ```python
   import click
   from rich.console import Console

   console = Console()

   @click.command()
   @click.argument("input_path", type=click.Path(exists=True))
   @click.option("--verbose", "-v", is_flag=True, help="Verbose output")
   def new_command(input_path: str, verbose: bool):
       """Command description."""
       console.print(f"[bold blue]Processing:[/bold blue] {input_path}")
       # Implementation...
   ```
3. Register command in `src/b4_thesis/cli.py`:
   ```python
   from b4_thesis.commands import new_command

   main.add_command(new_command.new_command)
   ```

## Important Design Principles

### 1. Error Handling
- Display user input errors with clear messages (use Rich)
- Catch exceptions appropriately and convert to user-friendly error messages

### 2. Output
- Progress bars: Use `tqdm`
- Tables/decoration: Use `rich`
- Data output: Support JSON/CSV/TXT formats

### 3. Config Management
- Use Pydantic models in `core/config.py`
- Config file locations:
  - `~/.config/b4-thesis/config.json`
  - `./b4-thesis.json` (project root)

### 4. Testing
- Place tests corresponding to each command in `tests/`
- Use Click's `CliRunner` for CLI testing
- Coverage target: 80%+

## Common Development Tasks

### Adding Data Analysis Features
1. Implement in `commands/analyze.py` or new command file
2. Process with pandas/numpy
3. Display results with Rich table

### Adding Visualization Features
1. Add new plot type to `commands/visualize.py`
2. Draw with matplotlib/seaborn
3. Make DPI/size/style customizable via config

### Adding Statistical Metrics
1. Add new metrics to `commands/stats.py`
2. Leverage scipy/scikit-learn functions
3. Make selectable via `--metrics` option

## Debugging Tips

### CLI Debugging
```python
# Verbose debug output
console.print("[dim]Debug info here[/dim]")

# Display exception details
import traceback
console.print(f"[red]Error:[/red] {traceback.format_exc()}")
```

### Data Analysis Debugging
```python
# Check DataFrame
console.print(df.head())
console.print(df.info())
console.print(df.describe())
```

## Git Workflow

### Commit Granularity (Important)

**Commit frequently with appropriate granularity**

#### When to Commit
Create one commit for each of the following units:

1. **Feature Addition**
   - Add new command → 1 commit
   - Add option to command → 1 commit
   - Add test → 1 commit (or together with feature)

2. **Refactoring**
   - Organize one file → 1 commit
   - Extract/move function → 1 commit
   - Organize imports → 1 commit

3. **Documentation Updates**
   - Update README → 1 commit
   - Update CLAUDE.md → 1 commit
   - Add/fix comments → 1 commit

4. **Configuration Changes**
   - Add dependency → 1 commit
   - Change Ruff config → 1 commit
   - Update .gitignore → 1 commit

#### Bad Example (Too Coarse)
```bash
# ❌ Batch multiple changes together
git add .
git commit -m "feat: add various things"
```

#### Good Examples (Appropriate Granularity)
```bash
# ✅ Add new command
git add src/b4_thesis/commands/git_analysis.py
git commit -m "feat: add git analysis command

Add basic git repository analysis functionality"

# ✅ Add tests
git add tests/test_git_analysis.py
git commit -m "test: add tests for git analysis command"

# ✅ Add dependency
git add pyproject.toml uv.lock
git commit -m "chore: add gitpython dependency"

# ✅ Update documentation
git add README.md
git commit -m "docs: update README with git analysis usage"
```

### Pre-Commit Checklist
- [ ] `uv run ruff check --fix src/` for linting
- [ ] `uv run ruff format src/` for formatting
- [ ] `uv run pytest tests/` for tests (or just relevant tests)
- [ ] Add tests for new features
- [ ] Commit message is clear and specific
- [ ] 1 commit = 1 logical change

### Commit Message Convention
```
<type>: <subject>

<body>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation update
- style: Code style fix
- refactor: Refactoring
- test: Add/fix tests
- chore: Build/config changes
```

### Recommended Development Flow

```bash
# 1. Start new feature development
# 2. Implementation
# 3. Lint & format
uv run ruff check --fix src/ && uv run ruff format src/

# 4. Run tests
uv run pytest tests/

# 5. Check changes
git status
git diff

# 6. Stage only relevant files
git add src/b4_thesis/commands/new_feature.py

# 7. Commit
git commit -m "feat: add new feature

Detailed description of what this commit does"

# 8. Move to next change (e.g., add tests)
git add tests/test_new_feature.py
git commit -m "test: add tests for new feature"

# 9. Update docs as needed
git add README.md CLAUDE.md docs/task_breakdown.md
git commit -m "docs: update documentation for new feature"
```

### Commit Best Practices

1. **Small, Frequent Commits**
   - 1 change = 1 commit
   - Break work into small units

2. **Meaningful Units**
   - Commit when compile/tests pass
   - Don't commit half-finished work

3. **Clear Messages**
   - What was changed (What)
   - Why it was changed (Why)

4. **Only Related Files**
   - Avoid `git add .`
   - Carefully stage file by file

## Development Roadmap

**See [task_breakdown.md](docs/task_breakdown.md) for detailed task breakdown and roadmap.**

### Current Status Summary

- **Completed**: Phase 1-4, Phase 5.1-5.3, Phase 6
- **In Progress**: Phase 5.4-5.5
- **Planned**: Phase 7

**Test Status**: 282 tests passing (100% success rate)

**Code Quality**: ruff checks passing (0 errors)

## References

- [Click Documentation](https://click.palletsprojects.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pandas Documentation](https://pandas.pydata.org/docs/)

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'b4_thesis'`
```bash
# Solution: Reinstall in development mode
uv pip install -e .
```

**Issue**: Import order incorrect
```bash
# Solution: Auto-fix with Ruff
uv run ruff check --fix src/
```

**Issue**: Tests failing
```bash
# Solution: Run in verbose mode
uv run pytest tests/ -v
```

## Notes

- **Character Encoding**: All files saved as UTF-8
- **Line Endings**: LF (Unix format)
- **Data Files**: Not tracked by git (in .gitignore)
- **Output Files**: Use `output/`, `results/`, `plots/` directories (not tracked by git)

---

**Last Updated**: 2025-11-10 (Task list moved to task_breakdown.md)
**Maintainer**: Claude Code Development Team
