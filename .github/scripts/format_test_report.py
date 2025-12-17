import os
import re
import sys

# Constants
MIN_LINES_FOR_VALID_REPORT = 2
MIN_PARTS_IN_LINE = 3
MIN_PARTS_FOR_RESULT = 4
FILEPATH_INDEX = 1
FUNCTION_INDEX = 2
RESULT_INDEX = 3


def clean_cell(cell_content):
    """Clean the cell content by removing latex/color formatting."""
    content = cell_content.replace("$$", "")

    # Try to extract text inside \tt{...}
    match = re.search(r"\\tt\{(.*?)\}", content)
    if match:
        content = match.group(1)

    # Unescape underscores
    content = content.replace(r"\_", "_")

    return content.strip()


def parse_report_lines(lines):
    """Parse the report lines and group by filepath."""
    files = {}

    # Skip header (line 0) and separator (line 1)
    if len(lines) < MIN_LINES_FOR_VALID_REPORT:
        return files

    data_lines = lines[2:]

    for line in data_lines:
        if not line.strip():
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < MIN_PARTS_IN_LINE:
            continue

        filepath_cell = parts[FILEPATH_INDEX]
        filepath = clean_cell(filepath_cell)

        if filepath not in files:
            files[filepath] = []

        files[filepath].append(line)

    return files


def write_formatted_report(output_file, files):
    """Write the formatted report to the output file."""
    with open(output_file, "w", encoding="utf-8") as f:
        for filepath, rows in files.items():
            f.write(f"<details>\n<summary>{filepath}</summary>\n\n")
            f.write("| Function | Result |\n")
            f.write("| :--- | :---: |\n")

            for line in rows:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < MIN_PARTS_FOR_RESULT:
                    continue
                function_cell = parts[FUNCTION_INDEX]
                result_cell = parts[RESULT_INDEX]

                f.write(f"| {function_cell} | {result_cell} |\n")

            f.write("\n</details>\n\n")


def format_report(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found.")
        return

    with open(input_file, encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return

    files = parse_report_lines(lines)
    write_formatted_report(output_file, files)


if __name__ == "__main__":
    if len(sys.argv) < 3:  # noqa: PLR2004
        print("Usage: python format_test_report.py <input_file> <output_file>")
        sys.exit(1)

    format_report(sys.argv[1], sys.argv[2])
