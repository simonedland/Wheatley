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


def _normalize_path(path: str) -> str:
    return os.path.normpath(path).replace("\\", "/")


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
        filepath = _normalize_path(clean_cell(filepath_cell))

        if filepath not in files:
            files[filepath] = []

        files[filepath].append(line)

    return files


def parse_pytest_failures(report_path="pytest_report.txt"):
    """Parse pytest text report to map file path -> failure detail blocks."""
    if not os.path.exists(report_path):
        return {}

    failures = {}
    current_file = None
    buffer = []

    path_re = re.compile(r"([\w./-]*wheatley[^\s:]*\.py)")
    separator_re = re.compile(r"^=+")

    def _flush():
        nonlocal buffer, current_file
        if current_file and buffer:
            text = "".join(buffer).strip()
            if text:
                failures.setdefault(current_file, []).append(text)
        buffer = []

    with open(report_path, encoding="utf-8") as f:
        for line in f:
            m = path_re.search(line)
            if m and ("ERROR" in line or "FAILED" in line or line.startswith("E   ")):
                _flush()
                current_file = _normalize_path(m.group(1))
                buffer.append(line)
                continue
            if current_file:
                if separator_re.match(line):
                    _flush()
                    current_file = None
                    continue
                buffer.append(line)
        _flush()
    return failures


def write_formatted_report(output_file, files):
    """Write the formatted report to the output file with error details."""
    failure_map = parse_pytest_failures()
    with open(output_file, "w", encoding="utf-8") as f:
        for filepath, rows in files.items():
            norm_path = _normalize_path(filepath)
            f.write(f"<details>\n<summary>{filepath}</summary>\n\n")
            f.write("| Function | Result | Details |\n")
            f.write("| :--- | :---: | :--- |\n")

            for line in rows:
                parts = [clean_cell(p.strip()) for p in line.split("|")]
                if len(parts) < MIN_PARTS_FOR_RESULT:
                    continue
                function_cell = parts[FUNCTION_INDEX]
                result_cell = parts[RESULT_INDEX]
                detail_parts = parts[RESULT_INDEX + 1 :]
                details = " | ".join([p for p in detail_parts if p])
                if not details:
                    fail_blocks = failure_map.get(norm_path, [])
                    if fail_blocks:
                        snippet = fail_blocks[0]
                        details = snippet.replace("\n", "<br>")
                if not details:
                    details = "-"

                f.write(f"| {function_cell} | {result_cell} | {details} |\n")

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
