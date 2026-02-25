# Weather Skill (wttr.in)

无需 API Key 的天气查询 skill，基于 [wttr.in](https://wttr.in)。

## 特点

- 无需注册、无 API Key
- 通过 HTTP 获取 JSON 格式天气数据
- 目前返回：城市名、天气描述、温度（摄氏度）、湿度、风速

## 使用方式

```python
from skills.weather import WeatherSkill

skill = WeatherSkill()
result = skill.get_weather("北京")
print(result)
```

返回示例（结构大致如下，具体字段视 wttr.in 返回而定）：

```json
{
  "city": "北京",
  "description": "Partly cloudy",
  "temperature": 23.0,
  "humidity": 60,
  "wind_speed": 10.0,
  "raw": { "...": "wttr.in 原始返回" }
}
```

## 命令行测试（可选）

你也可以直接在命令行测试 wttr.in：

```bash
curl 'https://wttr.in/Beijing?format=j1'
```