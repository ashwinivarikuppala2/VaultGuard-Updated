import zlib
from typing import Tuple


class CompressionService:
    """Lossless stream compression service for backup payloads."""

    @staticmethod
    def compress(data: bytes, level: int = 6) -> Tuple[bytes, int, int, float]:
        """Compress raw bytes using zlib.
        
        Returns:
            Tuple of (compressed_bytes, original_size, compressed_size, compression_ratio)
        """
        original_size = len(data)
        if original_size == 0:
            return b"", 0, 0, 1.0

        compressed = zlib.compress(data, level=level)
        compressed_size = len(compressed)
        ratio = round(compressed_size / original_size, 4) if original_size > 0 else 1.0

        return compressed, original_size, compressed_size, ratio

    @staticmethod
    def decompress(compressed_data: bytes) -> bytes:
        """Decompress zlib compressed bytes."""
        if not compressed_data:
            return b""
        return zlib.decompress(compressed_data)


compression_service = CompressionService()

