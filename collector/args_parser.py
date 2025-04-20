import argparse


def build_parser():
    parser = argparse.ArgumentParser(description="Web automation script")
    subparsers = parser.add_subparsers(
        dest="agent_method", required=True, help="Agent methods"
    )

    # Subparser for 'skyvern'
    parser_skyvern = subparsers.add_parser("skyvern", help="Skyvern agent method")
    parser_skyvern.add_argument(
        "--site", type=str, default="amazon.com", help="The site URL"
    )
    parser_skyvern.add_argument(
        "--task", type=str, default="Buy shoes", help="The task to perform"
    )
    parser_skyvern.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Total number of seconds before timeout",
    )
    parser_skyvern.add_argument(
        "--site-category", type=str, default="", help="The category of the site"
    )
    parser_skyvern.add_argument(
        "--darkpattern-category", type=str, default="", help="Dark pattern category"
    )
    parser_skyvern.add_argument(
        "--real-site", type=str, default="", help="Real site URL"
    )

    # Subparser for 'WebArena'
    parser_webarena = subparsers.add_parser("webarena", help="WebArena agent method")
    parser_webarena.add_argument(
        "--site", type=str, default="amazon.com", help="The site URL"
    )
    parser_webarena.add_argument(
        "--task", type=str, default="Buy shoes", help="The task to perform"
    )
    parser_webarena.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Total number of seconds before timeout",
    )
    parser_webarena.add_argument(
        "--site-category", type=str, default="", help="The category of the site"
    )
    parser_webarena.add_argument(
        "--darkpattern-category", type=str, default="", help="Dark pattern category"
    )
    parser_webarena.add_argument(
        "--real-site", type=str, default="", help="Real site URL"
    )

    # Subparser for 'VisualWebArena'
    parser_visualwebarena = subparsers.add_parser(
        "visualwebarena", help="WebArena agent method"
    )
    parser_visualwebarena.add_argument(
        "--site", type=str, default="amazon.com", help="The site URL"
    )
    parser_visualwebarena.add_argument(
        "--task", type=str, default="Buy shoes", help="The task to perform"
    )
    parser_visualwebarena.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Total number of seconds before timeout",
    )
    parser_visualwebarena.add_argument(
        "--site-category", type=str, default="", help="The category of the site"
    )
    parser_visualwebarena.add_argument(
        "--darkpattern-category", type=str, default="", help="Dark pattern category"
    )
    parser_visualwebarena.add_argument(
        "--real-site", type=str, default="", help="Real site URL"
    )

    # Subparser for 'human'
    parser_human = subparsers.add_parser("human", help="Human agent method")
    parser_human.add_argument(
        "--site", type=str, default="amazon.com", help="The site URL"
    )
    parser_human.add_argument(
        "--task", type=str, default="Buy shoes", help="The task to perform"
    )
    parser_human.add_argument(
        "--has-adblocker", action="store_true", help="Use adblocker (default: False)"
    )
    parser_human.add_argument(
        "--no-has-adblocker",
        action="store_false",
        dest="has_adblocker",
        help="Disable adblocker (default: False)",
    )
    parser_human.add_argument(
        "--simulate-ios", action="store_true", help="Simulate iOS (default: False)"
    )
    parser_human.add_argument(
        "--use-cookies",
        action="store_true",
        help="Whether or not to use cookies across sessions",
    )
    parser_human.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Total number of seconds before timeout",
    )
    parser_human.add_argument(
        "--concurrency", type=int, default=1, help="Number of tasks to run concurrently"
    )
    parser_human.add_argument(
        "--total-tasks", type=int, default=1, help="Total number of tasks to run"
    )
    parser_human.add_argument(
        "--site-category", type=str, default="", help="The category of the site"
    )
    parser_human.add_argument(
        "--darkpattern-category", type=str, default="", help="Dark pattern category"
    )

    # Subparser for 'multion'
    parser_multion = subparsers.add_parser(
        "multion", help="Multion Extension agent method"
    )
    parser_multion.add_argument(
        "--site", type=str, default="amazon.com", help="The site URL"
    )
    parser_multion.add_argument(
        "--task", type=str, default="Buy shoes", help="The task to perform"
    )
    parser_multion.add_argument(
        "--synthetic-site", type=str, default="", help="Synthetic site if any"
    )
    parser_multion.add_argument(
        "--has-adblocker", action="store_true", help="Use adblocker (default: False)"
    )
    parser_multion.add_argument(
        "--no-has-adblocker",
        action="store_false",
        dest="has_adblocker",
        help="Disable adblocker (default: False)",
    )
    parser_multion.add_argument(
        "--use-cookies",
        action="store_true",
        help="Whether or not to use cookies across sessions",
    )
    parser_multion.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Total number of seconds before timeout",
    )
    parser_multion.add_argument(
        "--concurrency", type=int, default=1, help="Number of tasks to run concurrently"
    )
    parser_multion.add_argument(
        "--total-tasks", type=int, default=1, help="Total number of tasks to run"
    )
    parser_multion.add_argument(
        "--site-category", type=str, default="", help="The category of the site"
    )
    parser_multion.add_argument(
        "--darkpattern-category", type=str, default="", help="Dark pattern category"
    )

    # Subparser for 'dobrowser'
    parser_multion = subparsers.add_parser(
        "dobrowser", help="DoBrowser Extension agent method"
    )
    parser_multion.add_argument(
        "--site", type=str, default="amazon.com", help="The site URL"
    )
    parser_multion.add_argument(
        "--task", type=str, default="Buy shoes", help="The task to perform"
    )
    parser_multion.add_argument(
        "--synthetic-site", type=str, default="", help="Synthetic site if any"
    )
    parser_multion.add_argument(
        "--has-adblocker", action="store_true", help="Use adblocker (default: False)"
    )
    parser_multion.add_argument(
        "--no-has-adblocker",
        action="store_false",
        dest="has_adblocker",
        help="Disable adblocker (default: False)",
    )
    parser_multion.add_argument(
        "--use-cookies",
        action="store_true",
        help="Whether or not to use cookies across sessions",
    )
    parser_multion.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Total number of seconds before timeout",
    )
    parser_multion.add_argument(
        "--concurrency", type=int, default=1, help="Number of tasks to run concurrently"
    )
    parser_multion.add_argument(
        "--total-tasks", type=int, default=1, help="Total number of tasks to run"
    )
    parser_multion.add_argument(
        "--site-category", type=str, default="", help="The category of the site"
    )
    parser_multion.add_argument(
        "--darkpattern-category", type=str, default="", help="Dark pattern category"
    )

    # Subparser for 'browseruse'
    parser_browseruse = subparsers.add_parser(
        "browseruse", help="BrowserUse agent method"
    )
    parser_browseruse.add_argument(
        "--site", type=str, default="amazon.com", help="The site URL"
    )
    parser_browseruse.add_argument(
        "--task", type=str, default="Buy shoes", help="The task to perform"
    )
    parser_browseruse.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Total number of seconds before timeout",
    )
    parser_browseruse.add_argument(
        "--site-category", type=str, default="", help="The category of the site"
    )
    parser_browseruse.add_argument(
        "--darkpattern-category", type=str, default="", help="Dark pattern category"
    )
    parser_browseruse.add_argument(
        "--real-site", type=str, default="", help="Real site URL"
    )

    # Subparser for 'agent e'
    parser_agente = subparsers.add_parser(
        "agente", help="Agent E agent method"
    )
    parser_agente.add_argument(
        "--site", type=str, default="amazon.com", help="The site URL"
    )
    parser_agente.add_argument(
        "--task", type=str, default="Buy shoes", help="The task to perform"
    )
    parser_agente.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Total number of seconds before timeout",
    )
    parser_agente.add_argument(
        "--site-category", type=str, default="", help="The category of the site"
    )
    parser_agente.add_argument(
        "--darkpattern-category", type=str, default="", help="Dark pattern category"
    )
    parser_agente.add_argument(
        "--real-site", type=str, default="", help="Real site URL"
    )
    return parser
