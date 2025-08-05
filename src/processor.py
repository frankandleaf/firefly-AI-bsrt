from src.environment.text_env import TextEnv
from src.model import call_openai_chat
from src.prompts.instruction import INSTRUCTION
from src.prompts.observation import OBSERVATION

class InteractionProcessor:
    def __init__(self, env, model="gemini-2.5-flash"):
        self.all_items = [
            "magnifying_glass",
            "cigarette_pack",
            "beer",
            "handsaw",
            "handcuffs",
            "burner_phone",
            "inverter",
            "adrenaline",
            "expired_medicine"
        ]
        self.env = env
        self.model = model
        self.player_items:list[str] = []
        self.dealer_items:list[str] = []
        
    def get_item_name(self, item_id, is_player=True):
        if is_player:
            if item_id >= len(self.player_items):
                raise ValueError("Item ID out of range for player items")
            return self.player_items[item_id]
        else:
            if item_id >= len(self.dealer_items):
                raise ValueError("Item ID out of range for dealer items")
            return self.dealer_items[item_id]
        
    def shoot(self, target:str):
        if target == "self":
            print("Shooting self")
        elif target == "dealer":
            print("Shooting dealer")
        else:
            print("Invalid target")
        self.env.shoot(target)

    def use(self, items:list):
        if len(items) == 1:
            item = self.get_item_name(int(items[0]))
            if item == "adrenaline":
                raise ValueError("Adrenaline usage requires a target item")            
            print(f"Using item: {item}")
            self.env.use(items, item)
            # Logic for using a single item
        elif len(items) == 2:
            item = self.get_item_name(int(items[0]))
            if item != "adrenaline":
                raise ValueError("First item must be adrenaline for stealing")
            item = self.get_item_name(int(items[1]), is_player=False)
            if item == "adrenaline":
                raise ValueError("Cannot steal adrenaline")
            print(f"Using item: {item} and stealing {item} from dealer")
            self.env.use(items, item)
            
        
    def act(self, action):
        action = action.split()
        if action[0] == "shoot":
            try:
                self.shoot(action[1])
            except ValueError as e:
                print(f"Error: {e}")
                return
            pass
        elif action[0] == "use":
            try:
                self.use(action[1:])    
            except ValueError as e:
                print(f"Error: {e}")
                return
            pass
        
    def play(self):
        if self.env.start_game():
            messages = [
                {"role": "system", "content": INSTRUCTION},
            ]
            while True and not self.env.is_closed():
                print("当前游戏屏幕:\n", self.env.get_current_screen())
                state = self.env.get_current_game_state()
                print("当前游戏状态:\n", state)
                self.player_items = state["player_items"]
                self.dealer_items = state["dealer_items"]
                messages.append(
                    {"role": "user", "content": OBSERVATION.format(
                        player_health=state["player_health"],
                        dealer_health=state["dealer_health"],
                        max_health=state["max_health"],
                        live_count=state["bullet_types"]["live_shell"],
                        blank_count=state["bullet_types"]["blank"],
                        player_items="\n".join([f"{i}.{item}" for i, item in enumerate(state["player_items"])]),
                        dealer_items="\n".join([f"{i}.{item}" for i, item in enumerate(state["dealer_items"])]),
                        use_info=state["use_info"]
                    )}
                )
                response = call_openai_chat(messages, model=self.model).content
                print("AI Response:", response)
                messages.append({"role": "assistant", "content": response})
                # 从 Action: 后面开始提取行动
                action = response.split("Action:")[-1].strip()
                print("AI Action:", action)
                self.act(action)

        else:
            print("游戏开始失败")
            return

if __name__ == "__main__":
    env = TextEnv()
    processor = InteractionProcessor(env, "gemini-2.5-flash")
    processor.play()
    