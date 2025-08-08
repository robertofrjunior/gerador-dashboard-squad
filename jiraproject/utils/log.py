"""Utilitário simples de logs padronizados para o app."""

def info(message: str) -> None:
    print(f"ℹ️ {message}")


def ok(message: str) -> None:
    print(f"✅ {message}")


def warn(message: str) -> None:
    print(f"⚠️ {message}")


def error(message: str) -> None:
    print(f"❌ {message}")


