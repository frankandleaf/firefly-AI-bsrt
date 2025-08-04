OBSERVATION = """
现在是你的回合
你的生命值：{player_health}/{max_health}
庄家的生命值：{dealer_health}/{max_health}
当前枪膛中的子弹类型：实弹{live_count}发，空包弹{blank_count}发

你的道具列表：
{player_items}

庄家的道具列表：
{dealer_items}

使用道具后的信息：
{use_info}

请根据当前情况进行推理，并决定你的行动。你可以选择使用道具或射击。
"""