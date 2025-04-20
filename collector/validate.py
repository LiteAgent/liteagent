from argparse import ArgumentParser
from collector.validation_rules import VALIDATION_RULES


def validate_args(args, parser: ArgumentParser):
    agent_method = args.agent_method.lower()

    if agent_method not in VALIDATION_RULES:
        parser.error(
            f"Unknown agent method: '{args.agent_method}'. Valid options are: {', '.join(VALIDATION_RULES.keys())}."
        )

    rules = VALIDATION_RULES[agent_method]
    required_args = rules["required"]
    allowed_args = set(rules["allowed"])

    # Check for required arguments
    missing_args = [arg for arg in required_args if getattr(args, arg) in [None, ""]]
    if missing_args:
        parser.error(
            f"The following arguments are required for agent_method '{agent_method}': {', '.join('--' + arg.replace('_', '-') for arg in missing_args)}."
        )

    # Check for disallowed arguments
    provided_args = {
        arg for arg, value in vars(args).items() if value not in [None, False, "", 0]
    }
    disallowed_args = provided_args - allowed_args
    if disallowed_args:
        parser.error(
            f"The following arguments are not valid for agent_method '{agent_method}': {', '.join('--' + arg.replace('_', '-') for arg in disallowed_args)}."
        )
