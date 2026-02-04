"""
Dependencies для работы с настройками ноды
"""
from settings import Settings
from typing import Union
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from fastapi import Depends

from didcomm.crypto import EthKeyPair, KeyPair


async def get_settings() -> Settings:
    return Settings()


SettingsDepends = Annotated[Settings, Depends(get_settings)]


async def get_node_priv_key(settings: SettingsDepends) -> Union[EthKeyPair, KeyPair, None]:
    if settings.mnemonic.phrase:
        return EthKeyPair.from_mnemonic(settings.mnemonic.phrase.get_secret_value())
    elif settings.mnemonic.encrypted_phrase:
        return EthKeyPair.from_encrypted_mnemonic(settings.mnemonic.encrypted_phrase.get_secret_value())
    elif settings.pem:
        return KeyPair.from_pem(settings.pem)
    else:
        return None


PrivKeyDepends = Annotated[Union[EthKeyPair, KeyPair, None], Depends(get_node_priv_key)]
