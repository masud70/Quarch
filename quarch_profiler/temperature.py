"""CPU package temperature, read from Linux's thermal zones."""

import glob


class CpuTemperature:
    """Reads the CPU package temperature (the x86_pkg_temp thermal zone).

        temp = CpuTemperature()
        temp.read()          # e.g. 49.0 (degC), NaN if the zone does not exist
    """

    def __init__(self):
        self.zone = self._find_pkg_temp_zone()

    @property
    def available(self):
        return self.zone is not None

    def read(self):
        """CPU package temperature in degC, NaN if the machine has no x86_pkg_temp zone."""
        if self.zone is None:
            return float("nan")
        with open(f"{self.zone}/temp") as f:
            return int(f.read().strip()) / 1000.0

    @staticmethod
    def _find_pkg_temp_zone():
        """thermal_zone path whose type is x86_pkg_temp (CPU package), or None."""
        for zone in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
            try:
                with open(f"{zone}/type") as f:
                    if f.read().strip() == "x86_pkg_temp":
                        return zone
            except OSError:
                continue
        return None


if __name__ == "__main__":
    temperature = CpuTemperature()
    print(f"CPU package temperature zone: {temperature.zone or 'not found'}")
    print(f"CPU package temperature: {temperature.read()} degC")
