import requests
from dataclasses import dataclass
from typing import Any, Dict, Optional


class WeatherAPIError(Exception):
    """天气 API 调用异常"""
    pass


@dataclass
class WeatherResult:
    city: str
    description: str
    temperature: Optional[float]
    humidity: Optional[int]
    wind_speed: Optional[float]
    raw: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "city": self.city,
            "description": self.description,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "raw": self.raw,
        }


class WeatherSkill:
    """基于 wttr.in 的无密钥天气查询 Skill。

    wttr.in 特点：
    - 不需要注册、无需 API Key
    - 通过 HTTP 调用，支持 JSON 输出

    官方文档示例：
    - curl wttr.in/Shanghai?format=j1
    """

    def __init__(self, session: Optional[requests.Session] = None, base_url: str = "https://wttr.in"):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def get_weather(self, city: str) -> Dict[str, Any]:
        """通过城市名称查询当前天气。

        :param city: 城市名，例如 "Beijing" 或 "北京"
        :return: 字典形式的天气结果
        """
        url = f"{self.base_url}/{city}"
        params = {"format": "j1"}  # JSON 输出

        try:
            resp = self.session.get(url, params=params, timeout=10)
        except requests.RequestException as e:
            raise WeatherAPIError(f"请求天气服务失败: {e}") from e

        if resp.status_code != 200:
            raise WeatherAPIError(f"天气服务返回错误状态码 {resp.status_code}: {resp.text}")

        data = resp.json()

        # wttr.in 的 JSON 结构文档不算正式，这里做尽量健壮的解析
        try:
            current = data["current_condition"][0]
            weather_desc_list = current.get("weatherDesc", [])
            description = weather_desc_list[0].get("value") if weather_desc_list else "N/A"

            # 温度字段通常是摄氏度字符串，例如 "23"
            temp_c = current.get("temp_C")
            temp_c_val: Optional[float]
            try:
                temp_c_val = float(temp_c) if temp_c is not None else None
            except (TypeError, ValueError):
                temp_c_val = None

            humidity = None
            try:
                if current.get("humidity") is not None:
                    humidity = int(current["humidity"])
            except (TypeError, ValueError):
                humidity = None

            wind_speed = None
            try:
                if current.get("windspeedKmph") is not None:
                    wind_speed = float(current["windspeedKmph"])
            except (TypeError, ValueError):
                wind_speed = None

            city_name = city
        except (KeyError, IndexError, TypeError) as e:
            raise WeatherAPIError(f"解析天气数据失败: {e}; 原始数据: {data}") from e

        result = WeatherResult(
            city=city_name,
            description=description,
            temperature=temp_c_val,
            humidity=humidity,
            wind_speed=wind_speed,
            raw=data,
        )

        return result.to_dict()