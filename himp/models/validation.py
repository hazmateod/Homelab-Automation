"""
Validation model.
"""

from dataclasses import dataclass, field


@dataclass
class Validation:

    plugin: str

    passed: bool

    checks: list = field(default_factory=list)

    def add_check(self, name, passed):

        self.checks.append(
            {
                "name": name,
                "passed": passed,
            }
        )

    def passed_checks(self):

        return sum(
            1
            for check in self.checks
            if check["passed"]
        )

    def failed_checks(self):

        return sum(
            1
            for check in self.checks
            if not check["passed"]
        )

    def total_checks(self):

        return len(self.checks)

    def success_rate(self):

        if not self.checks:
            return 0.0

        return round(
            self.passed_checks()
            / self.total_checks()
            * 100,
            1,
        )
