"""
乐意AI - 命令行入口

使用方式:
    python main.py              # 启动CLI对话
    python main.py --help       # 查看帮助
    python main.py --model gpt-4o-mini  # 指定模型
"""

import sys
import os
import argparse

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_config():
    """加载配置文件"""
    import yaml

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    if not os.path.exists(config_path):
        print(f"[错误] 未找到配置文件: {config_path}")
        print("请确保 config.yaml 文件存在")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="乐意AI - 个人AI助手")
    parser.add_argument("--backend", choices=["deepseek", "openai"], help="指定后端")
    parser.add_argument("--model", help="指定模型名称")
    parser.add_argument("--temperature", type=float, help="温度参数 (0.0-2.0)")
    parser.add_argument("--version", action="store_true", help="显示版本信息")
    args = parser.parse_args()

    if args.version:
        print("乐意AI v0.1.0")
        print("个人AI助手 - 基于云端大模型API")
        return

    # 加载配置
    config = load_config()

    # 命令行参数覆盖配置
    if args.backend:
        config["llm"]["backend"] = args.backend
    if args.model:
        config["llm"]["model"] = args.model
    if args.temperature is not None:
        config["llm"]["temperature"] = args.temperature

    # 创建LLM客户端
    try:
        from llm.factory import create_llm
        llm = create_llm(config)
    except ValueError as e:
        print(f"\n[配置错误] {e}")
        print("\n请编辑 .env 文件填入你的API密钥，然后重试。")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 创建LLM客户端失败: {e}")
        sys.exit(1)

    # 启动CLI
    from ui.cli import CLI
    cli = CLI(llm, config)
    cli.run()


if __name__ == "__main__":
    main()