from hashlib import sha256
from pathlib import Path


def safe_filename(filename: str | None) -> str:
    """清理用户上传文件名，避免路径穿越。"""
    if not filename:
        raise ValueError("文件名不能为空。")
    safe_name = Path(filename).name.strip()
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("文件名不合法。")
    return safe_name


def file_suffix(filename: str | None) -> str:
    """获取小写文件扩展名。"""
    return Path(safe_filename(filename)).suffix.lower()


def validate_file_extension(filename: str | None, allowed_extensions: set[str]) -> str:
    """校验文件扩展名，并返回安全文件名。"""
    safe_name = safe_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in allowed_extensions:
        allowed = "、".join(sorted(allowed_extensions))
        raise ValueError(f"暂不支持该文件类型，允许的扩展名：{allowed}")
    return safe_name


def sha256_hex(data: bytes) -> str:
    """计算二进制内容的 SHA-256 摘要。"""
    return sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    """分块计算文件 SHA-256，避免大文件一次性读入内存。"""
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def new_sha256_digest():
    """创建可分块更新的 SHA-256 对象。"""
    return sha256()


def unlink_if_exists(path: Path) -> None:
    """删除本地文件；文件不存在时不报错。"""
    path.unlink(missing_ok=True)
