# python/m5/homework_filled/agent.py
"""m5.2 作业模板的参考版本，TODO 1 和 TODO 2 已经填好，
你可以部署它并在 Studio 中对话，或者用同一文件夹下的 call_agent_api.py
通过 API 查询它。这只是一个可能的答案，你的答案可能不同。尽情探索！"""

from langchain_core.tools import tool

from deepagents import create_deep_agent
from models import model

EXTREME_WEATHER_FACTS = {
    "hottest": "The hottest air temperature ever reliably recorded on Earth's surface was 56.7°C (134°F), in Death Valley, California, in July 1913.",
    "coldest": "The coldest temperature ever recorded on Earth's surface was -89.2°C (-128.6°F), at Vostok Station, Antarctica, in July 1983.",
    "windiest": "The highest surface wind speed ever measured was 408 km/h (253 mph), during a tornado near Bridge Creek, Oklahoma, in 1999.",
    "wettest": "Mawsynram, India receives the most average annual rainfall of any inhabited place on Earth, over 11,000 mm (about 467 inches) a year.",
}


# TODO 1 已填写
@tool
def lookup_extreme_weather(category: str) -> str:
    """查询一个极端天气的事实。category 是以下之一：hottest、coldest、windiest、wettest。"""
    return EXTREME_WEATHER_FACTS.get(
        category.lower(),
        f"No record on file for '{category}'. Try hottest, coldest, windiest, or wettest.",
    )


# TODO 2 已填写
SYSTEM_PROMPT = """你是 Storm Watch，一位喝了咖啡、语速略快的追风者，
正在天气最恶劣的地方做现场直播。回答天气纪录类问题之前，一定要先调用
lookup_extreme_weather，然后像现场报道一样把事实播报出来：语气紧迫、略带
戏剧性，最后平静地收尾。"""

# `langgraph.json` 指向这个模块级变量："./agent.py:graph"。
graph = create_deep_agent(model=model, tools=[lookup_extreme_weather], system_prompt=SYSTEM_PROMPT)