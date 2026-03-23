import os
import re
import shutil
import subprocess
import tempfile
import stat
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class VpnLocation:
    iso_code: str
    country: str
    city: str
    ping_estimate: int

    def display_label(self) -> str:
        return f"{self.city}, {self.country}  (~{self.ping_estimate} ms)"

    def connect_argument(self) -> str:
        """The value passed to `adguardvpn-cli connect -l`."""
        return self.city


@dataclass
class VpnStatus:
    is_connected: bool
    location_name: str = ""
    raw_output: str = ""


# ---------------------------------------------------------------------------
# ANSI escape stripping
# ---------------------------------------------------------------------------

ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi_codes(text: str) -> str:
    """Remove all ANSI escape sequences from a string."""
    return ANSI_ESCAPE_PATTERN.sub("", text)


# ---------------------------------------------------------------------------
# SUDO_ASKPASS helper detection
# ---------------------------------------------------------------------------

# Candidate programs that can show a graphical password prompt.
# sudo will call whichever one we point SUDO_ASKPASS at, passing the prompt
# text as $1, and expects the password on stdout.
_ASKPASS_PROGRAM_CANDIDATES = [
    "x11-ssh-askpass",       # ssh-askpass-gnome / openssh-askpass on Ubuntu/Mint
    "ssh-askpass-gnome",     # explicit gnome variant
    "ssh-askpass",           # generic symlink
    "ksshaskpass",           # KDE variant
]


def _find_askpass_program() -> Optional[str]:
    """
    Return the absolute path of the first usable askpass program found,
    or None if none is available.
    """
    for program_name in _ASKPASS_PROGRAM_CANDIDATES:
        full_path = shutil.which(program_name)
        if full_path:
            print(f"[backend] Found askpass program: {full_path}")
            return full_path

    # Last resort: try zenity (GTK dialog tool present on most Cinnamon desktops)
    zenity_path = shutil.which("zenity")
    if zenity_path:
        print(f"[backend] Will use zenity as askpass fallback: {zenity_path}")
        return None  # zenity needs a wrapper script — handled separately

    print("[backend] WARNING: No graphical askpass program found.")
    return None


def _create_zenity_askpass_script() -> Optional[str]:
    """
    Write a tiny shell script that wraps zenity as an askpass helper and
    return its path.  The caller is responsible for deleting it afterwards.

    zenity --password outputs the typed password on stdout, which is exactly
    what sudo expects from an askpass program.
    """
    zenity_path = shutil.which("zenity")
    if not zenity_path:
        return None

    script_content = (
        "#!/bin/sh\n"
        f'{zenity_path} --password --title="AdGuard VPN" '
        '--text="AdGuard VPN needs administrator privileges to manage the VPN tunnel."\n'
    )

    try:
        script_file = tempfile.NamedTemporaryFile(
            mode="w",
            prefix="adguardvpn_askpass_",
            suffix=".sh",
            delete=False,
        )
        script_file.write(script_content)
        script_file.flush()
        script_file.close()

        # Make the script executable
        os.chmod(script_file.name, stat.S_IRWXU)
        print(f"[backend] Created zenity askpass script: {script_file.name}")
        return script_file.name
    except Exception as error:
        print(f"[backend] Could not create zenity askpass script: {error}")
        return None


# ---------------------------------------------------------------------------
# Core backend class
# ---------------------------------------------------------------------------

class AdGuardVpnBackend:
    """
    Wraps adguardvpn-cli subcommands and manages privilege escalation.

    Every public method returns (success: bool, message: str) so the
    frontend never needs to parse raw CLI output directly.
    """

    CLI_EXECUTABLE = "adguardvpn-cli"

    def __init__(self):
        self._askpass_program_path = _find_askpass_program()
        self._zenity_script_path: Optional[str] = None

        # If no standard askpass found, prepare a zenity wrapper
        if self._askpass_program_path is None:
            self._zenity_script_path = _create_zenity_askpass_script()
            if self._zenity_script_path:
                self._askpass_program_path = self._zenity_script_path

        if self._askpass_program_path:
            print(f"[backend] Will use askpass: {self._askpass_program_path}")
        else:
            print(
                "[backend] WARNING: No askpass helper available. "
                "sudo may prompt in the terminal instead."
            )

    def __del__(self):
        """Clean up temporary zenity script if we created one."""
        if self._zenity_script_path and os.path.exists(self._zenity_script_path):
            try:
                os.unlink(self._zenity_script_path)
                print(f"[backend] Removed temporary askpass script: {self._zenity_script_path}")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal subprocess helpers
    # ------------------------------------------------------------------

    def _build_user_environment(self) -> dict:
        """
        Build an environment dict for subprocess calls.

        Starts from the current process environment (which has the real user's
        HOME, XDG_*, DISPLAY, DBUS_SESSION_BUS_ADDRESS, etc.) and injects
        SUDO_ASKPASS so that `sudo -A` knows which program to call.
        """
        environment = os.environ.copy()
        if self._askpass_program_path:
            environment["SUDO_ASKPASS"] = self._askpass_program_path
            print(f"[backend] SUDO_ASKPASS set to: {self._askpass_program_path}")
        return environment

    def _run_plain_command(self, arguments: list) -> tuple:
        """
        Run adguardvpn-cli without elevated privileges.
        Returns (success: bool, cleaned_output: str).
        """
        full_command = [self.CLI_EXECUTABLE] + arguments
        print(f"[backend] Running plain command: {full_command}")
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=30,
                env=self._build_user_environment(),
            )
            combined_output = result.stdout + result.stderr
            clean_output = strip_ansi_codes(combined_output).strip()
            success = result.returncode == 0
            print(f"[backend] Exit code: {result.returncode}")
            print(f"[backend] Output preview: {clean_output[:300]}")
            return success, clean_output
        except FileNotFoundError:
            message = (
                f"'{self.CLI_EXECUTABLE}' not found.\n"
                "Please make sure AdGuard VPN CLI is installed."
            )
            print(f"[backend] ERROR: {message}")
            return False, message
        except subprocess.TimeoutExpired:
            message = "Command timed out after 30 seconds."
            print(f"[backend] ERROR: {message}")
            return False, message
        except Exception as error:
            message = f"Unexpected error: {error}"
            print(f"[backend] ERROR: {message}")
            return False, message

    def _run_privileged_command(self, arguments: list) -> tuple:
        """
        Run adguardvpn-cli with root privileges via:

            sudo -A -E adguardvpn-cli <arguments>

        -A  → use SUDO_ASKPASS program for the graphical password dialog
        -E  → preserve the caller's environment (crucially: HOME) so that
              adguardvpn-cli can find the login session in
              ~/.local/share/adguardvpn-cli

        sudo exit codes of interest:
          1   → authentication failed / wrong password
          (cancelled askpass also returns non-zero)
        """
        sudo_path = shutil.which("sudo")
        if not sudo_path:
            print("[backend] ERROR: sudo not found — cannot escalate privileges.")
            return False, "sudo is not installed. Cannot escalate privileges."

        cli_path = shutil.which(self.CLI_EXECUTABLE)
        if not cli_path:
            message = (
                f"'{self.CLI_EXECUTABLE}' not found.\n"
                "Please make sure AdGuard VPN CLI is installed."
            )
            print(f"[backend] ERROR: {message}")
            return False, message

        # Use the full path to the CLI so sudo can find it regardless of PATH
        full_command = [sudo_path, "-A", "-E", cli_path] + arguments

        print(f"[backend] Running privileged command: {full_command}")
        environment = self._build_user_environment()

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=60,
                env=environment,
            )
            combined_output = result.stdout + result.stderr
            clean_output = strip_ansi_codes(combined_output).strip()
            print(f"[backend] Privileged exit code: {result.returncode}")
            print(f"[backend] Privileged output preview: {clean_output[:300]}")

            # sudo returns 1 when the askpass program is cancelled or fails
            if result.returncode != 0 and not clean_output:
                return False, "Authentication cancelled or failed."

            success = result.returncode == 0
            return success, clean_output

        except subprocess.TimeoutExpired:
            message = "Privileged command timed out after 60 seconds."
            print(f"[backend] ERROR: {message}")
            return False, message
        except Exception as error:
            message = f"Unexpected error during privileged command: {error}"
            print(f"[backend] ERROR: {message}")
            return False, message

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_status(self) -> VpnStatus:
        """Query the current VPN connection status."""
        print("[backend] Querying VPN status...")
        success, output = self._run_plain_command(["status"])
        if not output:
            return VpnStatus(is_connected=False, raw_output="Could not get status.")

        lower_output = output.lower()
        is_connected = (
            "connected" in lower_output
            and "not connected" not in lower_output
            and "disconnected" not in lower_output
        )

        # Try to extract a human-readable location name from the output
        location_name = ""
        for line in output.splitlines():
            lower_line = line.lower()
            if "connected to" in lower_line or "location:" in lower_line:
                location_name = line.strip()
                break

        print(f"[backend] is_connected={is_connected}  location={location_name!r}")
        return VpnStatus(
            is_connected=is_connected,
            location_name=location_name,
            raw_output=output,
        )

    def list_locations(self) -> tuple:
        """
        Fetch all available VPN locations from the CLI.
        Returns (success: bool, locations: list[VpnLocation]).
        The list is sorted by ping estimate (fastest first).
        """
        print("[backend] Fetching location list...")
        success, output = self._run_plain_command(["list-locations"])
        if not success:
            print("[backend] Failed to fetch locations.")
            return False, []

        locations = _parse_locations_from_output(output)
        print(f"[backend] Parsed {len(locations)} locations.")
        return True, locations

    def connect(self, city_name: Optional[str] = None) -> tuple:
        """
        Connect to VPN.

        Pass city_name=None (or empty string) to let the CLI choose
        automatically (fastest available server).
        Uses sudo -A -E so the graphical password dialog appears and the
        user's HOME (login session) is preserved.
        """
        if city_name:
            print(f"[backend] Connecting to city: {city_name!r}")
            arguments = ["connect", "-l", city_name]
        else:
            print("[backend] Connecting to fastest location (automatic).")
            arguments = ["connect"]

        success, output = self._run_privileged_command(arguments)

        # The CLI sometimes exits 0 and sometimes doesn't, but always prints
        # "Successfully Connected" on success — check both.
        connection_succeeded = success or "successfully connected" in output.lower()
        return connection_succeeded, output

    def disconnect(self) -> tuple:
        """Disconnect from VPN. Does not require elevated privileges."""
        print("[backend] Disconnecting from VPN...")
        return self._run_privileged_command(["disconnect"])


# ---------------------------------------------------------------------------
# Location list parser
# ---------------------------------------------------------------------------

def _parse_locations_from_output(raw_output: str) -> list:
    """
    Parse the tabular output of `adguardvpn-cli list-locations`.

    Expected format (after ANSI stripping):
        ISO   COUNTRY              CITY                           PING ESTIMATE
        MD    Moldova              Chișinău                       20
        ...
    Column layout uses 2+ spaces as separator, which we exploit.
    """
    locations = []
    lines = raw_output.splitlines()
    header_found = False

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        # Detect and skip the header row
        if "ISO" in stripped_line and "COUNTRY" in stripped_line:
            header_found = True
            continue

        if not header_found:
            continue

        try:
            location = _parse_single_location_line(stripped_line)
            if location is not None:
                locations.append(location)
        except Exception as parse_error:
            print(f"[backend] Skipping unparseable line: {stripped_line!r} — {parse_error}")
            continue

    locations.sort(key=lambda location_entry: location_entry.ping_estimate)
    return locations


def _parse_single_location_line(line: str) -> Optional[VpnLocation]:
    """
    Parse one data row from the locations table.

    Splits on runs of 2+ spaces (matches the CLI's fixed-width layout).
    Expected parts: [ISO, COUNTRY, CITY, PING_ESTIMATE]
    """
    parts = re.split(r"\s{2,}", line.strip())

    if len(parts) >= 4:
        iso_code = parts[0].strip()
        country = parts[1].strip()
        city = parts[2].strip()
        ping_str = parts[3].strip()
    elif len(parts) == 3:
        # Occasionally country and city merge into one column
        iso_code = parts[0].strip()
        city_country_combined = parts[1].strip()
        ping_str = parts[2].strip()
        # Try splitting city_country on comma or space
        if "," in city_country_combined:
            country, _, city = city_country_combined.partition(",")
        else:
            token_list = city_country_combined.split()
            mid = max(1, len(token_list) // 2)
            country = " ".join(token_list[:mid])
            city = " ".join(token_list[mid:])
    else:
        return None

    # Ping may contain extra text; extract leading digits only
    ping_match = re.match(r"(\d+)", ping_str)
    if not ping_match:
        return None
    ping_estimate = int(ping_match.group(1))

    # Sanity-check: ISO code should be 2 uppercase letters
    if not re.match(r"^[A-Z]{2}$", iso_code):
        return None

    return VpnLocation(
        iso_code=iso_code,
        country=country,
        city=city,
        ping_estimate=ping_estimate,
    )
