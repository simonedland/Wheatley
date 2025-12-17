import os
import sys

import requests


# Configuration
def get_github_token() -> str:
    """Get GitHub token from env."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()

    print("GH_TOKEN / GITHUB_TOKEN is not set. Exiting.")
    sys.exit(1)


GITHUB_TOKEN = get_github_token()
REPO = os.environ.get("GITHUB_REPOSITORY")
BRANCH = os.environ.get("BRANCH_NAME")
REPORT_FILE = os.environ.get("REPORT_FILE", "quality-report.txt")
RUN_ID = os.environ.get("GITHUB_RUN_ID")
SERVER_URL = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
MIN_ERROR_PARTS = 3

# HTTP Status Codes (used for response validation)
HTTP_NO_CONTENT = 204  # No content response from successful POST/DELETE operations
HTTP_NOT_FOUND = 404  # Resource not found

if not GITHUB_TOKEN or not REPO or not BRANCH:
    print("Missing environment variables: GH_TOKEN, GITHUB_REPOSITORY, or BRANCH_NAME")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

API_URL = f"https://api.github.com/repos/{REPO}"


def get_issues(label_branch):
    """Fetch all open issues with the specific branch label."""
    issues = []
    page = 1
    while True:
        url = f"{API_URL}/issues?state=open&labels=code-quality,{label_branch}&per_page=100&page={page}"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        issues.extend(data)
        page += 1
    return issues


def _handle_ruff_format(line, file_errors):
    """Handle Ruff format output."""
    if not line.startswith("Would reformat: "):
        return False

    filename = line[len("Would reformat: ") :].strip()
    if filename not in file_errors:
        file_errors[filename] = []
    file_errors[filename].append("File needs formatting (run `ruff format .`)")
    return True


def _handle_pytest_failure(line, file_errors):
    """Handle Pytest failure output."""
    if " FAILED " not in line and not line.endswith(" FAILED"):
        return False

    # Format: tests/test_file.py::test_function FAILED [ 0%]
    test_parts = line.split("::")
    if len(test_parts) > 1:
        filename = test_parts[0].strip()
        message = line
        if filename not in file_errors:
            file_errors[filename] = []
        file_errors[filename].append(message)
        return True
    return False


def _handle_standard_error(line, file_errors):
    """Handle standard error output."""
    parts = line.split(":", 3)
    if len(parts) < MIN_ERROR_PARTS:
        return

    # Basic validation: 2nd part should be a line number
    if not parts[1].strip().isdigit():
        return

    filename = parts[0]
    if filename not in file_errors:
        file_errors[filename] = []
    file_errors[filename].append(line)


def _process_line(line, file_errors):
    """Process a single line from the report."""
    if _handle_ruff_format(line, file_errors):
        return

    if _handle_pytest_failure(line, file_errors):
        return

    _handle_standard_error(line, file_errors)


def parse_report(file_path):
    """Parse the quality report. Assumes format: file:line:col: code message"""
    file_errors = {}
    if not os.path.exists(file_path):
        return file_errors

    with open(file_path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            _process_line(line, file_errors)
    return file_errors


def create_issue(filename, errors):
    title = f"Code quality issues in {filename}"
    error_count = len(errors)

    # Join all errors without truncation
    preview = "\n".join(errors)

    body = (
        f"### 🚨 Code Quality Issues in `{filename}`\n\n"
        f"Found **{error_count}** issues.\n\n"
        f"```\n{preview}\n```\n\n"
        f"**Branch:** `{BRANCH}`\n"
        f"**Run:** {SERVER_URL}/{REPO}/actions/runs/{RUN_ID}\n"
    )

    labels = ["code-quality", f"branch:{BRANCH}"]

    data = {"title": title, "body": body, "labels": labels}

    resp = requests.post(f"{API_URL}/issues", headers=HEADERS, json=data)
    resp.raise_for_status()
    issue_data = resp.json()
    print(f"Created issue for {filename}: {issue_data['html_url']}")


def update_issue(issue, filename, errors):
    error_count = len(errors)

    # Join all errors without truncation
    preview = "\n".join(errors)

    # Construct the new body
    body = (
        f"### 🚨 Code Quality Issues in `{filename}`\n\n"
        f"Found **{error_count}** issues.\n\n"
        f"```\n{preview}\n```\n\n"
        f"**Branch:** `{BRANCH}`\n"
        f"**Run:** {SERVER_URL}/{REPO}/actions/runs/{RUN_ID}\n"
        f"\n*Updated via CI*"
    )

    # Check if the error content is the same to avoid unnecessary updates (e.g. just Run ID changing)
    if issue.get("body") and preview in issue["body"]:
        print(f"Issue #{issue['number']} for {filename} is up to date.")
        return

    data = {"body": body}
    resp = requests.patch(
        f"{API_URL}/issues/{issue['number']}", headers=HEADERS, json=data
    )
    resp.raise_for_status()
    print(f"Updated issue #{issue['number']} for {filename}")


def close_issue(issue, filename):
    comment_body = f"✅ All code quality issues in `{filename}` resolved on branch `{BRANCH}`. Closing."

    # Add comment
    requests.post(
        f"{API_URL}/issues/{issue['number']}/comments",
        headers=HEADERS,
        json={"body": comment_body},
    )

    # Close issue
    resp = requests.patch(
        f"{API_URL}/issues/{issue['number']}", headers=HEADERS, json={"state": "closed"}
    )
    resp.raise_for_status()
    print(f"Closed issue #{issue['number']} for {filename}")


def main():
    print(f"Processing quality report: {REPORT_FILE}")
    file_errors = parse_report(REPORT_FILE)

    label_branch = f"branch:{BRANCH}"
    existing_issues = get_issues(label_branch)

    # Map filename to issue
    file_to_issue = {}
    for issue in existing_issues:
        # Extract filename from title "Code quality issues in filename"
        title = issue["title"]
        if title.startswith("Code quality issues in "):
            fname = title.replace("Code quality issues in ", "")
            file_to_issue[fname] = issue

    # Create or Update
    for filename, errors in file_errors.items():
        if filename in file_to_issue:
            update_issue(file_to_issue[filename], filename, errors)
        else:
            create_issue(filename, errors)

    # Close resolved
    for filename, issue in file_to_issue.items():
        if filename not in file_errors:
            close_issue(issue, filename)


if __name__ == "__main__":
    main()
