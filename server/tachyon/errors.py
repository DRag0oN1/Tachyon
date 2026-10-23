class TachyonError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status

    def public(self):
        return {"code": self.code, "message": self.message, "retryable": False}
