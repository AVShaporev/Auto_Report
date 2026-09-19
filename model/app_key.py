"""Ключи организации. Сейчас один — «signature»: RSA-пара для офлайн-подписи
узором (телефон шифрует узор открытым ключом, сервер расшифровывает при
синхронизации). Создаётся при первом обращении, см. service/customer_signature.py."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base, int_pk


class App_Key(Base):
    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String(50), unique=True)
    private_pem: Mapped[str] = mapped_column(Text)
    public_pem: Mapped[str] = mapped_column(Text)
