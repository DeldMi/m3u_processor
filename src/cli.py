import os
import asyncio
from src.manager import PlaylistManager

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    manager = PlaylistManager(root_dir)

    print("==================================================")
    print(" INICIANDO PROCESSAMENTO E TESTE DE STREAMS M3U   ")
    print("==================================================")

    channels = manager.load_input_channels()
    total = len(channels)
    print(f"[*] Total de canais unicos identificados na pasta input/: {total}")

    if total == 0:
        print("[!] Nenhum canal encontrado. Deposite arquivos .m3u, .m3u8 ou .txt em input/.")
        return

    print("[*] Testando conectividade e latencia de cada fluxo...")
    valid, invalid = asyncio.run(manager.validate_all_channels(channels))

    print(f"[+] Canais funcionais: {len(valid)}")
    print(f"[-] Canais inoperantes (removidos): {len(invalid)}")

    print("[*] Particionando listas (limite: 400 canais por arquivo)...")
    created = manager.save_partitioned_playlists(valid)

    log_path = manager.generate_audit_log(total, valid, invalid, created)
    print(f"[+] Concluido! Listas geradas ({len(created)} partes): {', '.join(created)}")
    print(f"[+] Relatorio detalhado salvo em: {log_path}")

if __name__ == "__main__":
    main()