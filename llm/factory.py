"""
乐意AI - LLM客户端工厂

根据配置自动创建对应的模型客户端实例。
"""

import os
from typing import Optional
from dotenv import load_dotenv

from .base import BaseLLMClient
from .deepseek import DeepSeekClient
from .openai import OpenAIClient


# 加载 .env 文件
load_dotenv()


def create_llm(config: dict) -> BaseLLMClient:
    """
    根据配置创建LLM客户端实例

    Args:
        config: 配置字典（从 config.yaml 加载）

    Returns:
        BaseLLMClient 实例

    Raises:
        ValueError: 未知的后端类型
        ValueError: API密钥未配置
    """
    llm_config = config.get("llm", {})
    backend = llm_config.get("backend", "deepseek").lower()

    if backend == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY") or llm_config.get("api_key", "")
        if not api_key or api_key == "your_deepseek_api_key_here":
            raise ValueError(
                "DeepSeek API密钥未配置！\n"
                "请复制 .env.example 为 .env，填入你的 DEEPSEEK_API_KEY\n"
                "获取地址: https://platform.deepseek.com"
            )
        return DeepSeekClient(
            api_key=api_key,
            model=llm_config.get("model", "deepseek-chat"),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 4096),
            top_p=llm_config.get("top_p", 0.9),
        )

    elif backend == "openai":
        api_key = os.getenv("OPENAI_API_KEY") or llm_config.get("api_key", "")
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError(
                "OpenAI API密钥未配置！\n"
                "请复制 .env.example 为 .env，填入你的 OPENAI_API_KEY\n"
                "获取地址: https://platform.openai.com"
            )
        return OpenAIClient(
            api_key=api_key,
            model=llm_config.get("model", "gpt-4o-mini"),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 4096),
            top_p=llm_config.get("top_p", 0.9),
        )

    elif backend == "github":
        api_key = os.getenv("GITHUB_API_KEY") or os.getenv("OPENAI_API_KEY") or llm_config.get("api_key", "")
        if not api_key or api_key == "your_github_api_key_here":
            raise ValueError(
                "GitHub Models API密钥未配置！\n"
                "请复制 .env.example 为 .env，填入你的 GITHUB_API_KEY\n"
                "获取地址: https://github.com/marketplace/models"
            )
        return OpenAIClient(
            api_key=api_key,
            base_url="https://models.inference.ai.azure.com",
            model=llm_config.get("model", "gpt-4o-mini"),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 4096),
            top_p=llm_config.get("top_p", 0.9),
        )

    elif backend == "chatanywhere":
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("CHATANYWHERE_API_KEY") or llm_config.get("api_key", "")
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError(
                "ChatAnywhere API密钥未配置！\n"
                "请复制 .env.example 为 .env，填入你的 OPENAI_API_KEY\n"
                "获取地址: https://api.chatanywhere.tech"
            )
        return OpenAIClient(
            api_key=api_key,
            base_url="https://api.chatanywhere.tech",
            model=llm_config.get("model", "gpt-4o-mini"),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 4096),
            top_p=llm_config.get("top_p", 0.9),
        )

    else:
        raise ValueError(f"未知的后端类型: {backend}，支持的后端: deepseek, openai, github, chatanywhere")


def list_available_backends() -> list[str]:
    """列出可用的后端类型"""
    return ["deepseek", "openai", "github", "chatanywhere"]