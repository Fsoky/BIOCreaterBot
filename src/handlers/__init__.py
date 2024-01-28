from aiogram import Router


def setup_message_routers() -> Router:
    from . import start, bio

    router = Router()
    router.include_router(start.router)
    router.include_router(bio.router)
    return router