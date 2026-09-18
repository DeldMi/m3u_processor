"""Operações de manutenção restritas a diretórios conhecidos.

Nenhuma função deste módulo aceita um caminho arbitrário como destino de
remoção. Os diretórios são derivados da raiz da aplicação.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


class MaintenanceService:
    """Calcula e executa limpezas seletivas sem atravessar a raiz permitida."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir).resolve()
        self.roots = {
            "cache": self.base_dir / "cache",
            "temp": self.base_dir / "temp",
            "output": self.base_dir / "output",
            "logs": self.base_dir / "logs",
        }

    def _safe_root(self, category: str) -> Path:
        path = self.roots.get(category)
        if path is None:
            raise ValueError("Categoria de manutenção inválida.")
        path = path.resolve()
        if path == self.base_dir or self.base_dir not in path.parents:
            raise ValueError("Diretório de manutenção inválido.")
        return path

    @staticmethod
    def _size(path: Path) -> int:
        if not path.exists():
            return 0
        if path.is_file():
            return path.stat().st_size
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())

    def inspect(self) -> dict[str, Any]:
        """Retorna tamanho e existência sem modificar o sistema."""
        categories = {
            key: {"path": str(path), "exists": path.exists(), "bytes": self._size(path)}
            for key, path in self.roots.items()
        }
        usage = shutil.disk_usage(self.base_dir)
        return {"categories": categories, "disk": {"total": usage.total, "free": usage.free, "used": usage.used}}

    def clear(self, categories: list[str]) -> dict[str, Any]:
        """Remove apenas conteúdo dentro das categorias explicitamente escolhidas."""
        if not isinstance(categories, list) or not categories:
            raise ValueError("Informe ao menos uma categoria.")
        result = {"categories": [], "files": 0, "bytes": 0}
        for category in categories:
            root = self._safe_root(category)
            if not root.exists():
                result["categories"].append({"category": category, "files": 0, "bytes": 0})
                continue
            before = self._size(root)
            count = 0
            for item in list(root.rglob("*")):
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    count += 1
            for directory in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            result["files"] += count
            result["bytes"] += before
            result["categories"].append({"category": category, "files": count, "bytes": before})
        return result
