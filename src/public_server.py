from src.app import PUBLIC_ONLY, app, manager


if __name__ == "__main__":
    if not PUBLIC_ONLY:
        raise RuntimeError("O servidor público precisa ser iniciado com PUBLIC_ONLY=1")
    cfg = manager.config_mgr.get_all()
    app.run(host=cfg["PUBLIC_HOST"], port=cfg["PUBLIC_PORT"], debug=False)