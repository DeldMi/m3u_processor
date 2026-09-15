import time
import asyncio
import aiohttp
from typing import Dict, Any, Tuple

async def test_stream(
    session: aiohttp.ClientSession, 
    channel: Dict[str, Any], 
    semaphore: asyncio.Semaphore, 
    user_agent: str, 
    timeout_sec: int
) -> Tuple[Dict[str, Any], bool, float, int]:
    url = channel["url"]
    headers = {
        "User-Agent": user_agent,
        "Range": "bytes=0-1024"
    }
    
    # Timeout segmentado para falhar rapido em sockets inoperantes
    client_timeout = aiohttp.ClientTimeout(
        total=timeout_sec,
        sock_connect=max(2, timeout_sec // 2),
        sock_read=max(2, timeout_sec // 2)
    )

    start_time = time.time()
    async with semaphore:
        try:
            async with session.get(url, headers=headers, timeout=client_timeout, allow_redirects=True) as response:
                latency = round((time.time() - start_time) * 1000, 2)
                if response.status in (200, 206):
                    return channel, True, latency, response.status
                return channel, False, latency, response.status
        except Exception:
            latency = round((time.time() - start_time) * 1000, 2)
            return channel, False, latency, 0