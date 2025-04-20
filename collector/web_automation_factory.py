from collector.web_automation_base import WebAutomationBase
from collector.web_automation_human import WebAutomationHuman
from collector.web_automation_multion import MultiOnExtensionWebAutomation
from collector.web_automation_dobrowser import DoBrowserExtensionWebAutomation
from collector.web_automation_skyvern import SkyvernWebAutomation
from collector.web_automation_webarena import WebArenaWebAutomation
from collector.web_automation_visualwebarena import VisualWebArenaWebAutomation
from collector.web_automation_browseruse import BrowserUseWebAutomation
from collector.web_automation_agente import AgentEWebAutomation

def create_web_automation(args) -> WebAutomationBase:
    try:
        agent_method = args.agent_method.lower()
        if agent_method == "multion":
            return MultiOnExtensionWebAutomation(
                site=args.site,
                task=args.task,
                darkpattern_category=args.darkpattern_category,
                use_cookies=args.use_cookies,
                agent_method=agent_method,
                has_adblocker=args.has_adblocker,
                site_category=args.site_category,
            )
        elif agent_method == "human":
            return WebAutomationHuman(
                site=args.site,
                task=args.task,
                darkpattern_category=args.darkpattern_category,
                use_cookies=args.use_cookies,
                agent_method=agent_method,
                has_adblocker=args.has_adblocker,
                simulate_ios=args.simulate_ios,
                site_category=args.site_category,
            )
        elif agent_method == "skyvern":
            return SkyvernWebAutomation(
                site=args.site,
                task=args.task,
                darkpattern_category=args.darkpattern_category,
                agent_method=agent_method,
                site_category=args.site_category,
                real_site=args.real_site,
            )
        elif agent_method == "webarena":
            return WebArenaWebAutomation(
                site=args.site,
                task=args.task,
                darkpattern_category=args.darkpattern_category,
                agent_method=agent_method,
                site_category=args.site_category,
                real_site=args.real_site,
            )
        elif agent_method == "visualwebarena":
            return VisualWebArenaWebAutomation(
                site=args.site,
                task=args.task,
                darkpattern_category=args.darkpattern_category,
                agent_method=agent_method,
                site_category=args.site_category,
                real_site=args.real_site,
            )
        elif agent_method == "dobrowser":
            return DoBrowserExtensionWebAutomation(
                site=args.site,
                task=args.task,
                darkpattern_category=args.darkpattern_category,
                use_cookies=args.use_cookies,
                agent_method=agent_method,
                has_adblocker=args.has_adblocker,
                site_category=args.site_category,
            )
        elif agent_method == "browseruse":
            return BrowserUseWebAutomation(
                site=args.site,
                task=args.task,
                darkpattern_category=args.darkpattern_category,
                agent_method=agent_method,
                site_category=args.site_category,
                real_site=args.real_site,
            )
        elif agent_method == "agente":
            return AgentEWebAutomation(
                site=args.site,
                task=args.task,
                darkpattern_category=args.darkpattern_category,
                agent_method=agent_method,
                site_category=args.site_category,
                real_site=args.real_site,
            )
        else:
            raise ValueError(f"Unsupported agent method: {agent_method}")
    except AttributeError as e:
        raise ValueError("Missing required argument") from e
    except Exception as e:
        raise RuntimeError("An error occurred while creating web automation") from e
