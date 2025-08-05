# firefly-AI-bsrt
以LLM/MLLM为核心，自动游玩《恶魔轮盘》

目前支持在 [BuckshotRouletteCLI](https://github.com/OlafZhang/BuckshotRouletteCLI) 提供的纯文本环境中自动交互游玩。

## 运行

### 环境配置

```bash
git clone https://github.com/frankandleaf/firefly-AI-bsrt.git
cd firefly-AI-bsrt

# 安装 conda （可选）
conda create -n firefly-ai-bsrt python=3.12
conda activate firefly-ai-bsrt

# 安装依赖
pip install -r requirements.txt
```

同时请在环境中设置好 api 密钥等配置。
```bash
# 设置 OpenAI API 密钥
export OPENAI_API_KEY=your_openai_api_key
export OPENAI_BASE_URL=your_openai_base_url  # 可选 

# 设置 Gemini API 密钥
export GEMINI_API_KEY=your_gemini_api_key
export GEMINI_BASE_URL=your_gemini_base_url  # 可选
```

### 启动游戏

```bash
# 启动游戏
python -m src.main --config config/text.yaml
```

同时可在另一个终端中运行：

```bash
# 实时查看游戏
tail -f /tmp/game_output.log | cat
```

以实时观察游戏情况。