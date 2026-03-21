[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.4492665.svg)](https://doi.org/10.5281/zenodo.4492665)

FSE '21 paper implementation ([preprint](./camera-ready.pdf))<br>
DOI of submitted version executable file of NIL is `10.5281/zenodo.4492665`.

# NIL

NIL is a clone detector using N-gram, Inverted index, and LCS.
NIL provides scalable large-variance clone detection.

## Requirements

- JDK 21+

## Install & Usage

- Clone this repository (`git clone https://github.com/kusumotolab/NIL`)
- Move into NIL's directory (`cd NIL`) and build NIL (`./gradlew ShadowJar`)
- Run NIL (`java -jar ./build/libs/NIL-all.jar [options]`)
- Check the result files in `results/<timestamp>_<hash>/` directory
  - `result.csv`: Final output (ID format by default, full-path format with `--full-path` option)
  - `clone_pairs.csv`: Clone pairs in ID format (always generated)
  - `code_blocks.csv`: Detailed code block information for reference
  - **ID format** (default): `id1,id2,ngram_similarity,lcs_similarity`
    - Reduces file size by 90-95%
    - Reference `code_blocks.csv` for detailed information
  - **Full-path format** (`--full-path`): `/path/to/file_A,start_line_A,end_line_A,/path/to/file_B,start_line_B,end_line_B,ngram_similarity,lcs_similarity`
    - `ngram_similarity`: N-gram based similarity percentage (always present)
    - `lcs_similarity`: LCS based similarity percentage (present only when LCS verification was performed)
  - **BCE format** (`-bce`): `dir_A,file_A,start_line_A,end_line_A,dir_B,file_B,start_line_B,end_line_B,ngram_similarity,lcs_similarity`

## Options

|                 Name                  | Description                                                                                            |         Default          |
| :-----------------------------------: | :----------------------------------------------------------------------------------------------------- | :----------------------: |
|             `-s`,`--src`              | Input source directory. You must specify the target dir.                                               |           None           |
|          `-mil`,`--min-line`          | Minimum number of lines that a code fragment must be to be treated as a clone.                         |           `6`            |
|         `-mit`,`--min-token`          | Minimum number of tokens that a code fragment must be to be treated as a clone.                        |           `50`           |
|            `-n`,`--n-gram`            | N for N-gram.                                                                                          |           `5`            |
|        `-p`,`--partition-size`        | The number of partitions.                                                                              |           `10`           |
|     `-f`,`--filtration-threshold`     | Threshold used in the filtration phase (%).                                                            |           `10`           |
|    `-v`,`--verification-threshold`    | Threshold used in the verificatioin phase (%).                                                         |           `70`           |
|            `-o`,`--output`            | Output file path (can include directory path).                                                         | `result_{n}_{f}_{v}.csv` |
|           `-t`,`--threads`            | The number of threads used for parallel execution (both the _Preprocess_ and _Clone detection_ phases) |       all threads        |
|           `-l`,`--language`           | [Target language](#Languages)                                                                          |          `java`          |
|             `--full-path`             | Output result with full file paths instead of IDs (default: ID format for compact output)              |         `false`          |
|        `-bce`,`--bigcloneeval`        | If you specify `-bce` option, NIL outputs result file feasible to BigCloneEval.                        |      not specified       |
| `-mif`,`--mutationinjectionframework` | If you specify `-mif` option, NIL outputs nothing except for the output file name as standard output.  |      not specified       |

## Languages

|  Name  |    Option     |   Extension   |
| :----: | :-----------: | :-----------: |
|  Java  |    `java`     |    `.java`    |
|   C    |      `c`      |   `.c`,`.h`   |
|  C++   |     `cpp`     | `.cpp`,`.hpp` |
|   C#   | `cs`,`csharp` |     `.cs`     |
| Python | `py`,`python` |     `.py`     |
| Kotlin | `kt`,`kotlin` |     `.kt`     |

If you execute NIL on 250-MLOC codebase, we recommend `-p` option to 135.

## Documentation

- [Usage Guide](./docs/NIL_USAGE_GUIDE.md) - Detailed usage guide including operation principles, Docker execution, and input/output formats
- [Docker Guide](./docs/DOCKER_GUIDE.md) - Comprehensive Docker execution guide with examples and troubleshooting
- [I/O Format](./docs/IO_FORMAT.md) - Detailed specification of input parameters and output formats
- [Architecture](./docs/ARCHITECTURE.md) - Internal architecture and implementation details

## Experiments, datasets, and baseline tools

- Please refer to [EXPERIMENTS.md](./EXPERIMENTS.md)
