from skills.weather import WeatherSkill

if __name__ == "__main__":
    skill = WeatherSkill()
    data = skill.get_weather("Beijing")
    print(data)