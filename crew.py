"""네이버 부동산 최저가 매물 찾기 - CrewAI 크루 정의"""

import yaml
from pathlib import Path
from crewai import Agent, Crew, Process, Task, LLM
from tools.naver_land import (
    search_apartment_complex,
    get_complex_listings,
    get_article_detail,
)

CONFIG_DIR = Path(__file__).parent / "config"


def _load_yaml(filename: str) -> dict:
    with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class NaverRealEstateCrew:
    """리서치 에이전트 + 자료 정리 에이전트로 구성된 크루"""

    def __init__(self):
        self.agents_config = _load_yaml("agents.yaml")
        self.tasks_config = _load_yaml("tasks.yaml")
        # Anthropic Claude 모델 사용
        self.llm = LLM(
            model="anthropic/claude-opus-4-6",
            temperature=0.1,
        )

    def _create_research_agent(self) -> Agent:
        cfg = self.agents_config["research_agent"]
        return Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[search_apartment_complex, get_complex_listings, get_article_detail],
            llm=self.llm,
            verbose=True,
        )

    def _create_organization_agent(self) -> Agent:
        cfg = self.agents_config["data_organization_agent"]
        return Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[],
            llm=self.llm,
            verbose=True,
        )

    def run(self, apartment_names: str):
        """크루를 실행하고 결과를 반환합니다."""
        research_agent = self._create_research_agent()
        organization_agent = self._create_organization_agent()

        # 태스크 생성
        research_cfg = self.tasks_config["research_task"]
        research_task = Task(
            description=research_cfg["description"].format(
                apartment_names=apartment_names
            ),
            expected_output=research_cfg["expected_output"],
            agent=research_agent,
        )

        organize_cfg = self.tasks_config["organize_task"]
        organize_task = Task(
            description=organize_cfg["description"],
            expected_output=organize_cfg["expected_output"],
            agent=organization_agent,
            context=[research_task],
        )

        # 크루 생성 및 실행
        crew = Crew(
            agents=[research_agent, organization_agent],
            tasks=[research_task, organize_task],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()
        return result
