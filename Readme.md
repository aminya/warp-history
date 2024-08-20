# Warp and McFly History to Shell History

This tool extracts command history from Warp and McFly and writes it to your shell's history file (either Bash or Zsh).

This allows you to have a unified command history across all your terminals and shell sessions.

It also fixes [the issue](https://github.com/cantino/mcfly/issues/435) where Warp is not able to search through the whole command history.

## Features

- Extracts command history from Warp terminal.
- Extracts command history from McFly.
- Writes the combined history to the specified shell history file.
- Backs up the existing shell history file before writing.

## Requirements

- Python 3.x
- Warp terminal with history stored in `~/.local/state/warp-terminal/warp.sqlite`
- McFly installed and available in the system PATH

## Installation

1. Clone the repository:
    ```sh
    git clone <repository-url>
    cd <repository-directory>
    ```

## Usage

Run the script with the desired shell type:

```sh
python ./warp-history.py --shell bash
```

or

```sh
python ./warp-history.py --shell zsh
```

## Command-Line Arguments

- `-shell`: Specify the shell type (bash or zsh). Default is bash.

## Example

```sh
python ./warp-history.py --shell zsh
```

This command will extract the history from Warp and McFly and write it to the Zsh history file.

## Notes

- The existing shell history file will be backed up with a `.bak` extension.
- You need to restart your shell to apply the changes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## Acknowledgements

- [Warp Terminal](https://www.warp.dev/)
- [McFly](https://github.com/cantino/mcfly)

## Contact

For any questions or suggestions, please open an issue in the repository.
