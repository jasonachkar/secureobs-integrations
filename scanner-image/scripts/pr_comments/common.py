MARKER = "<!-- secureobs-scanner -->"


def build_comment(is_blocking: bool) -> str:
    if is_blocking:
        status = "⛔ **Pipeline blocked** — critical findings detected. Resolve all blocking findings before merging."
    else:
        status = "✅ No blocking findings detected."

    return (
        f"{MARKER}\n"
        f"## SecureObs Security Scan\n\n"
        f"{status}\n\n"
        f"_View full details in your [SecureObs dashboard](https://secureobs-dashboard.azurewebsites.net)._"
    )
