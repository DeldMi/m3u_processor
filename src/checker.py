import ssl
import time
import asyncio
import aiohttp
from typing import Dict, Any, Tuple

def create_ssl_context(allow_insecure: bool = False) -> ssl.SSLContext:
    """Cria TLS seguro por padrão; permite certificados inválidos somente por opção explícita."""
    if not allow_insecure:
        return ssl.create_default_context()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


# Compatibilidade para integrações antigas; não deve ser usada em novos fluxos.
def create_unverified_ssl_context() -> ssl.SSLContext:
    return create_ssl_context(allow_insecure=True)

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
        "Accept": "*/*",
        "Range": "bytes=0-1024"  # RFC 7233: leitura parcial sem baixar o arquivo de video
    }
    
    client_timeout = aiohttp.ClientTimeout(
        total=timeout_sec,
        sock_connect=max(2, timeout_sec // 2),
        sock_read=max(2, timeout_sec // 2)
    )

    start_time = time.time()
    async with semaphore:
        try:
            async with session.get(
                url, 
                headers=headers, 
                timeout=client_timeout, 
                allow_redirects=True
            ) as response:
                latency = round((time.time() - start_time) * 1000, 2)
                # HTTP 200 (OK) ou 206 (Partial Content) atestam canal online
                if response.status in (200, 206):
                    return channel, True, latency, response.status
                return channel, False, latency, response.status
        except Exception:
            latency = round((time.time() - start_time) * 1000, 2)
            return channel, False, latency, 0