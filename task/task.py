from crewai import Task

from pathlib import Path

from agents.agents import NavigationAgent

from utils.yaml_load import load_yaml_dict

from logging_config import logger


class NavigationTask:

    def __init__(self):
        config_path = Path(__file__).resolve().parent.parent / "Config" / "Task.yaml"
        self.config_data = load_yaml_dict(str(config_path))
        self.agent_factory = NavigationAgent()

    def navigation_task(self) -> Task:

        return Task(

            description=self.config_data["Natural_language_task"]["description"],

            expected_output=self.config_data["Natural_language_task"]["expected_output"],

            agent=self.agent_factory.navigation_agent(),

        )
