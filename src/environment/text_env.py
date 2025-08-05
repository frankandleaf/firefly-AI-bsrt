import subprocess
import threading
import queue
import time
import re
import pty
import os
import select
from src.environment.base_env import BaseEnv

class TextEnv(BaseEnv):
    def __init__(self):
        super().__init__()
        self.process = None
        self.output_queue = queue.Queue()
        self.output_thread = None
        self.game_log = ""
        self.current_screen_lines = []
        self.self_turn = False
        self.is_inverted = False
        self.current_game_state = {
            "max_health": 0,
            "player_health": 0,
            "dealer_health": 0,
            "bullet_types": {
                "live_shell": 0,
                "blank": 0
            },
            "player_items": [],
            "dealer_items": [],
            "use_info": ""
        }
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self.icon_text_mapping = {
            "🔴": "live_shell",
            "🔵": "blank",
            "🔍": "magnifying_glass",
            "🚬": "cigarette_pack",
            "🍺": "beer",
            "🔪": "handsaw",
            "⛓️‍💥": "handcuffs",
            "📱": "burner_phone",
            "🔄️": "inverter",
            "️🔄": "inverter",
            "💉": "adrenaline",
            "💊": "expired_medicine",
            "⚡": "health",
            "☠️": "dealer"
        }
        self.text_icon_mapping = { 
            "live_shell": "🔴",
            "blank": "🔵",
            "magnifying_glass": "🔍",
            "cigarette_pack": "🚬",
            "beer": "🍺",
            "handsaw": "🔪",
            "handcuffs": "⛓️‍💥",
            "burner_phone": "📱",
            "inverter": "🔄️",
            "adrenaline": "💉",
            "expired_medicine": "💊",
            "health": "⚡",
            "dealer": "☠️" 
        }
        self.output_file = "/tmp/game_output.log"
        with open(self.output_file, 'w') as f:
            f.write("")  # 清空文件内容
        self.closed = False
    
    def _clean_ansi(self, text):
        """移除 ANSI 转义序列"""
        return self.ansi_escape.sub('', text)
        
    def _is_clear_screen(self, text):
        """检测是否包含清屏序列"""
        clear_patterns = ['\x1B[2J', '\x1B[H', '\x1Bc', '\033[2J', '\033[H', '\033c']
        return any(pattern in text for pattern in clear_patterns)
    
    def start_game(self):
        """启动游戏进程"""
        try:
            # 使用 pty 创建伪终端
            master, slave = pty.openpty()
            
            self.process = subprocess.Popen(
                ['python', 'BuckshotRouletteCLI/br.py'],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                text=True,
                universal_newlines=True
            )
            
            # 关闭从进程的 pty 端
            os.close(slave)
            
            # 将 master 转换为文件对象
            self.master_fd = master
            
            # 启动输出读取线程
            self.output_thread = threading.Thread(target=self._read_pty_output, daemon=True)
            self.output_thread.start()
            
            # 等待游戏初始化
            time.sleep(1)

            # 输入 2
            self.send_input("2")
            time.sleep(1)
            
            # 输入玩家名称
            self.send_input("SAM")
            time.sleep(25)
            
            print("游戏已启动，等待输出...")
            
            self.update_other_game_state(self.get_current_screen())

            return True
            
        except Exception as e:
            print(f"启动游戏失败: {e}")
            return False
            
    def _read_pty_output(self):
        """从 pty 读取输出"""
        try:
            buffer = ""
            
            while self.process and self.process.poll() is None:
                # 使用 select 检查是否有数据
                ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                
                if ready:
                    data = os.read(self.master_fd, 1024).decode('utf-8', errors='ignore')
                    buffer += data
                    
                    # 处理完整行
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        self._process_line(line)
                else:
                    # 没有新数据，处理缓冲区
                    if buffer.strip():
                        self._process_line(buffer)
                        buffer = ""
                        
        except Exception as e:
            print(f"读取错误: {e}")

    def _write_to_log(self, line):
        """写入到日志文件"""
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(f"{line}\n")
                f.flush()  # 立即刷新到磁盘
        except Exception as e:
            print(f"写入日志失败: {e}")

    def _process_line(self, line):
        """处理单行"""
        if self._is_clear_screen(line):
            self.current_screen_lines = []
            return
            
        self._write_to_log(line)
        clean_line = self._clean_ansi(line.strip())
        if clean_line:
            self.current_screen_lines.append(clean_line)
            self.output_queue.put(clean_line)
            if "打出了" in clean_line or "是一颗" in clean_line:
                if "实弹" in clean_line:
                    self.update_single_bullet("实弹")
                elif "空包弹" in clean_line:
                    self.update_single_bullet("空包弹")
            if "拼命砸碎了一个" in clean_line:
                self.is_inverted = not self.is_inverted
            if "请输入你的道具编号来使用道具，输入+来选择射击目标:" in clean_line:
                self.self_turn = True
            match = re.search(r'实弹(\d+)颗 空包弹(\d+)颗', clean_line)
            if match:
                self.update_bullet_types(match)
            # 提取每人 * 点生命值
            match = re.search(r'每人 (\d+) 点生命值', clean_line)
            if match:
                self.current_game_state['max_health'] = int(match.group(1))

    def get_current_screen(self):
        """获取当前屏幕显示的内容"""
        return "\n".join(self.current_screen_lines)
    
    def get_output(self, timeout=2.0):
        """获取游戏输出"""
        output_lines = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                line = self.output_queue.get(timeout=0.1)
                output_lines.append(line)
                self.game_log += line + "\n"
            except queue.Empty:
                # 如果没有更多输出，继续等待一小段时间
                if output_lines:  # 如果已经有输出，可能已经完成
                    time.sleep(0.1)
                continue
        
        return "\n".join(output_lines)
    
    def send_input(self, command: str):
        """向游戏发送输入"""
        if self.process and self.process.poll() is None:
            try:
                os.write(self.master_fd, (command + "\n").encode('utf-8'))
                return True
            except Exception as e:
                print(f"发送输入失败: {e}")
                return False
        return False
    
    def get_current_game_state(self):
        """获取当前游戏状态"""
        return self.current_game_state
    
    def get_game_log(self):
        """获取游戏日志"""
        return self.game_log
    
    def update_single_bullet(self, bullet_type: str):
        """更新单个子弹类型"""
        if bullet_type == "实弹":
            if not self.is_inverted:
                self.current_game_state['bullet_types']['live_shell'] -= 1
            else:
                self.current_game_state['bullet_types']['blank'] -= 1
        elif bullet_type == "空包弹":
            if not self.is_inverted:
                self.current_game_state['bullet_types']['blank'] -= 1
            else:
                self.current_game_state['bullet_types']['live_shell'] -= 1
        else:
            raise ValueError("未知的子弹类型")
        self.is_inverted = False  # 使用后重置逆转状态
    
    def update_bullet_types(self, match):
        """更新子弹类型"""
        # 从 match 中类似 实弹3颗 空包弹2颗 的格式提取子弹数量
        self.current_game_state['bullet_types']['live_shell'] = int(match.group(1))
        self.current_game_state['bullet_types']['blank'] = int(match.group(2))
        self.current_game_state["use_info"] = ""
        
    def update_other_game_state(self, obs):
        """更新其他游戏状态"""
        # print("更新时游戏状态:\n", obs)
        # 解析生命值 (⚡ 符号的数量)
        # 上方是庄家生命值，下方是玩家生命值
        lines = obs.split('\n')
        
        # 查找包含生命值符号的行
        for i, line in enumerate(lines):
            if '⚡' in line:
                health_count = line.count('⚡')
                # 判断是庄家还是玩家的生命值
                # 通过在表格中的位置判断：上半部分是庄家，下半部分是玩家
                if i < len(lines) // 2:
                    self.current_game_state['dealer_health'] = health_count
                else:
                    self.current_game_state['player_health'] = health_count

        dealer_items = []
        player_items = []
        
        for line in lines:
            # 匹配道具行格式: 数字.名称 的模式
            if re.search(r'\d+\.(magnifying_glass|cigarette_pack|beer|handsaw|handcuffs|burner_phone|inverter|adrenaline|expired_medicine)', line):
                # 提取所有道具名称
                items = re.findall(r'\d+\.(magnifying_glass|cigarette_pack|beer|handsaw|handcuffs|burner_phone|inverter|adrenaline|expired_medicine)', line)
                
                # 通过行的内容和位置判断是庄家还是玩家的道具
                line_index = lines.index(line)
                for item_match in items:
                    item_name = item_match  # 直接获取道具名称
                    if line_index < len(lines) // 2:
                        dealer_items.append(item_name)
                    else:
                        player_items.append(item_name)
                
        self.current_game_state['dealer_items'] = dealer_items
        self.current_game_state['player_items'] = player_items
        
    def update_use_info(self, obs):
        """更新使用道具后的信息"""
        self.current_game_state["use_info"] += obs + "\n"
        
    def update_use_info_after_shoot(self, is_beer: bool, is_self_turn_next: bool):
        """更新射击后的信息"""
        use_info = self.current_game_state["use_info"].split("\n")
        self.current_game_state["use_info"] = ""
        for line in use_info:
            if "手锯" in line:
                if is_beer:
                    self.current_game_state["use_info"] += line
            elif "手铐" in line:
                if is_self_turn_next:
                    self.current_game_state["use_info"] += line
            elif "手机" in line:
                match = re.search(r'第(\d+)发是(实弹|空包弹)', line)
                assert match, "手机使用信息格式错误"
                bullet_number = match.group(1)
                bullet_type = match.group(2)
                bullet_number = str(int(bullet_number) - 1)
                self.current_game_state["use_info"] += f"你使用了手机，第{bullet_number}发是{bullet_type}\n"

    def use(self, items:list, item_name:str = "", is_dealer_item:bool = False):
        # item_name = self.current_game_state["player_items"][int(items[0])]
        self.send_input(items[0])
        if not is_dealer_item:
            time.sleep(1)
            self.send_input("1")        
        if len(items) == 2:
            time.sleep(3)
            # item_name = self.current_game_state["dealer_items"][int(items[1])]
            self.use([items[1]], item_name, is_dealer_item=True)
        elif item_name == "magnifying_glass":
            time.sleep(9)
            obs = self.get_current_screen()
            if "实弹" in obs:
                self.update_use_info("你使用了放大镜，看到了一颗实弹")
            elif "空包弹" in obs:
                self.update_use_info("你使用了放大镜，看到了一颗空包弹")
            else:
                raise ValueError("无法识别子弹类型")
        elif item_name == "beer":
            time.sleep(8)
            obs = self.get_current_screen()
            if "实弹" in obs:
                self.update_single_bullet("实弹")
            elif "空包弹" in obs:
                self.update_single_bullet("空包弹")
            else:
                raise ValueError("无法识别子弹类型")
            self.update_use_info_after_shoot(is_beer=True, is_self_turn_next=True)
        elif item_name == "handsaw":
            self.update_use_info("你使用了手锯，下一次射击伤害提升至2点")
        elif item_name == "handcuffs":
            self.update_use_info("你使用了手铐，使庄家跳过下个回合")
        elif item_name == "burner_phone":
            time.sleep(6.5)
            obs = self.get_current_screen()
            if "真遗憾..." in obs:
                self.update_use_info("你使用了手机，但没有任何信息")
                return
            match = re.search(r'第(\d+)发是\.\.\.\n(实弹|空包弹)', obs)
            if match:
                bullet_number = match.group(1)
                bullet_type = match.group(2)
                self.update_use_info(f"你使用了手机，第{bullet_number}发是{bullet_type}")
            else:
                # raise ValueError("无法识别手机信息,当前屏幕内容:\n" + obs)
                print("无法识别手机信息,当前屏幕内容:\n" + obs)
        elif item_name == "inverter":
            self.update_use_info("你使用了逆转器，逆转了当前子弹类型")
            self.is_inverted = not self.is_inverted

        time.sleep(10)
        
        self.update_other_game_state(self.get_current_screen())
        
    def shoot(self, target: str):
        self.send_input("+")
        time.sleep(1)
        self.self_turn = False
        if target == "dealer":
            self.send_input("0")
            self.update_use_info_after_shoot(is_beer=False, is_self_turn_next=False)
        elif target == "self":
            self.send_input("1")
            self.update_use_info_after_shoot(is_beer=False, is_self_turn_next=True)
        else:
            raise ValueError("目标必须是 'dealer' 或 'self'")
        
        print("等待射击完行动...")
        count = 0
        while not self.is_self_turn():
            count += 1
            time.sleep(1)
            
            if "重新开始？" in self.get_current_screen():
                self.send_input("1")
                self.close()
                return
            if "加倍还是放弃？" in self.get_current_screen():
                self.clear_state()
                self.send_input("0")
        
        self.update_other_game_state(self.get_current_screen())
        
    def is_self_turn(self):
        """检查是否轮到玩家行动"""
        return self.self_turn
        
    def clear_state(self):
        """清除当前游戏状态"""
        self.current_game_state = {
            "max_health": 0,
            "player_health": 0,
            "dealer_health": 0,
            "bullet_types": {
                "live_shell": 0,
                "blank": 0
            },
            "player_items": [],
            "dealer_items": [],
            "use_info": ""
        }
        self.is_inverted = False
        self.self_turn = False
        
    def reset(self):
        """重置游戏"""
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        self.game_log = ""
        return self.start_game()
    
    def close(self):
        """关闭环境"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
        
        if self.output_thread:
            self.output_thread.join(timeout=1)
        self.closed = True
    
    def is_closed(self):
        """检查环境是否已关闭"""
        return self.closed
    
    def __del__(self):
        """析构函数，确保进程被正确关闭"""
        self.close()
        
        