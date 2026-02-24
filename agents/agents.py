
from crewai import Agent

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

import openai

import os

from pathlib import Path

from logging_config import logger

from utils.yaml_load import load_yaml_dict

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

llm = None

if not api_key:

    logger.warning("OPENAI_API_KEY not set; LLM features will be disabled and fallbacks used.")

else:

    try:

        openai.api_key = api_key

        llm = ChatOpenAI(api_key=api_key, model="gpt-4.1-mini")

    except Exception as e:

        logger.warning(f"Failed to initialize OpenAI LLM; falling back to simple instructions: {e}")

        llm = None


class NavigationAgent:

    def __init__(self):
        config_path = Path(__file__).resolve().parent.parent / "Config" / "Agents.yaml"
        self.config_data = load_yaml_dict(str(config_path))

    def navigation_agent(self) -> Agent:

        return Agent(

            role=self.config_data["Natural_language_agent"]["role"],

            goal=self.config_data["Natural_language_agent"]["goal"],

            backstory=self.config_data["Natural_language_agent"]["backstory"],

            verbose=True,

            llm=llm,

        )
