import argparse
import yaml

from src.environment.text_env import TextEnv
from src.processor import InteractionProcessor

def run(config):
    env_mapping = {
        "text": TextEnv,
    }
    if config["environment"] not in env_mapping:
        raise ValueError(f"Unsupported environment: {config['environment']}")
    
    env = env_mapping[config["environment"]](screen_refresh=config.get("screen_refresh", True))
    processor = InteractionProcessor(env, model=config["model"])
    processor.play()

def main():
    parser = argparse.ArgumentParser(description="启动 processor")
    parser.add_argument(
        "--config",
        type=str,
        default="config/text.yaml",
        help="配置文件路径，默认为 config/text.yaml"
    )
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    run(config)

if __name__ == "__main__":
    main()