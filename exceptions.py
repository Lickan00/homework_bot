class StatusHomeWorkException(Exception):
    """Класс исключения при проверке наличия статуса в словаре статусов."""
    def __init__(self):
        self.reason = 'Недокументированный статус домашней работы'

    def __str__(self):
        return self.reason


class HttpStatusException(Exception):
    """Класс исключения при проверке HTTPStatus."""


class ENDPOINTConnectError(Exception):
    """Класс исключения при подключению к API."""
    def __init__(self):
        self.reason = 'Не удалось получить доступ к ENDPOINT'

    def __str__(self):
        return self.reason
