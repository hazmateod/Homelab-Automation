"""
Validation Commands
"""

from himp.sdk.validator import PluginValidator


def run(args):

    validator = PluginValidator()

    results = validator.validate_all()

    passed = sum(
        1
        for result in results
        if result.passed
    )

    failed = len(results) - passed

    print("Plugin Validation")
    print("=================")
    print()

    for result in results:

        status = "PASS" if result.passed else "FAIL"

        print(
            f"{result.plugin} [{status}] "
            f"{result.success_rate():.1f}% "
            f"({result.passed_checks()}/{result.total_checks()})"
        )

        for check in result.checks:

            icon = "PASS" if check["passed"] else "FAIL"

            print(
                f"  {icon:<4} {check['name']}"
            )

        print()

    print("Summary")
    print("-------")
    print(f"Plugins Validated : {len(results)}")
    print(f"Passed            : {passed}")
    print(f"Failed            : {failed}")
