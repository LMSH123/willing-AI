"""
乐意AI - 安装验证脚本

运行: python verify.py
检查配置加载、客户端创建是否正常。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "[OK]"
FAIL = "[FAIL]"
INFO = "[i]"


def check_step(name: str, ok: bool, detail: str = ""):
    icon = PASS if ok else FAIL
    msg = f"  {icon} {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    return ok


def main():
    print()
    print("=" * 50)
    print("  乐意AI - 安装验证")
    print("=" * 50)
    print()

    all_ok = True

    # 1. Python version
    py_ok = sys.version_info >= (3, 9)
    all_ok &= check_step("Python版本", py_ok, sys.version.split()[0])

    # 2. Dependencies
    print()
    print("  [i] 检查依赖包:")
    try:
        import openai
        all_ok &= check_step("openai", True, openai.__version__)
    except ImportError:
        all_ok &= check_step("openai", False)

    try:
        import yaml
        all_ok &= check_step("pyyaml", True, yaml.__version__)
    except ImportError:
        all_ok &= check_step("pyyaml", False)

    try:
        import dotenv
        all_ok &= check_step("python-dotenv", True, dotenv.__version__ if hasattr(dotenv, "__version__") else "ok")
    except ImportError:
        all_ok &= check_step("python-dotenv", False)

    try:
        import rich
        all_ok &= check_step("rich", True, rich.__version__ if hasattr(rich, "__version__") else "ok")
    except ImportError:
        all_ok &= check_step("rich", False)

    # 3. File structure
    required_files = [
        "llm/__init__.py", "llm/base.py", "llm/deepseek.py",
        "llm/openai.py", "llm/factory.py",
        "config.yaml", ".env.example", "requirements.txt",
        "conversation/__init__.py", "memory/__init__.py",
        "knowledge/__init__.py", "tools/__init__.py",
        "ui/__init__.py", "ui/web/__init__.py",
    ]
    print()
    print("  [i] 检查项目文件结构:")
    for f in required_files:
        ok = os.path.exists(f)
        all_ok &= check_step(f, ok)

    # 4. Config loading
    print()
    print("  [i] 检查配置加载:")
    try:
        import yaml
        with open("config.yaml", "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        all_ok &= check_step("config.yaml 加载成功", True)
        backend = config.get("llm", {}).get("backend", "未知")
        model = config.get("llm", {}).get("model", "未知")
        check_step("当前配置后端", True, f"{backend} / {model}")
    except Exception as e:
        all_ok &= check_step("config.yaml 加载失败", False, str(e))

    # 5. API keys
    print()
    print("  [i] 检查API密钥:")
    if os.path.exists(".env"):
        check_step(".env 文件存在", True)
        from dotenv import load_dotenv
        load_dotenv()
        dk = os.getenv("DEEPSEEK_API_KEY", "")
        ok = bool(dk) and dk != "your_deepseek_api_key_here"
        all_ok &= check_step("DeepSeek API密钥", ok, "已配置" if ok else "未配置")
        ok2 = os.getenv("OPENAI_API_KEY", "")
        ok2_bool = bool(ok2) and ok2 != "your_openai_api_key_here"
        all_ok &= check_step("OpenAI API密钥", ok2_bool, "已配置" if ok2_bool else "未配置")
    else:
        check_step(".env 文件", False, "请复制 .env.example 为 .env 并填入API密钥")
        check_step("DeepSeek API密钥", False, "未配置")
        check_step("OpenAI API密钥", False, "未配置")

    # 6. LLM client creation test
    print()
    print("  [i] 测试客户端创建:")
    try:
        from llm.factory import create_llm, list_available_backends
        backends = list_available_backends()
        check_step("可用后端", True, ", ".join(backends))
        check_step("create_llm 函数导入", True)
    except Exception as e:
        all_ok &= check_step("导入失败", False, str(e))

    # Summary
    print()
    print("=" * 50)
    if all_ok:
        print(f"  {PASS} 所有检查通过！项目结构就绪。")
        print()
        print("  下一步:")
        print("  1. 复制 .env.example 为 .env")
        print("  2. 填入你的API密钥")
        print("  3. 运行 python main.py 启动 CLI 模式")
    else:
        print(f"  {FAIL} 部分检查未通过，请根据提示修复。")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()