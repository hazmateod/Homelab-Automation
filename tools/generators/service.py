"""
Builder Service.
"""

from __future__ import annotations

from .executor import PlanExecutor
from .generic import GenericGenerator
from .validator import TemplateValidator


class BuilderService:

    def __init__(self):

        self.generator = GenericGenerator()

        self.executor = PlanExecutor()

        self.validator = TemplateValidator()

    def validate(
        self,
        generator_type,
    ):

        return self.validator.validate(
            generator_type
        )

    def generate(
        self,
        generator_type,
        **context,
    ):

        self.validate(generator_type)

        plan, context = self.generator.build_plan(
            generator_type,
            **context,
        )

        self.executor.execute(
            plan,
            **context,
        )

        return plan

    def dry_run(
        self,
        generator_type,
        **context,
    ):

        self.validate(generator_type)

        plan, _ = self.generator.build_plan(
            generator_type,
            **context,
        )

        return plan
