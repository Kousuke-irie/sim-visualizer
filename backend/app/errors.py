"""業務エラー。

サービス層はこれらを投げるだけで HTTP を知らない。ステータスコードへの対応づけは
main.py の例外ハンドラ 1か所で行う（以前は各ルーターに try/except が14か所散らばっていた）。
detail はそのままユーザーに表示されるため、日本語で原因が分かる文にする。
"""


class AppError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    """指定された ID・ファイル・パスが存在しない（404）"""


class AccessDeniedError(AppError):
    """許可されていない場所へのアクセス（403）"""


class InvalidInputError(AppError):
    """入力ファイルやリクエストの内容が不正・未対応（400）"""


class PayloadTooLargeError(AppError):
    """アップロードが大きすぎる（413）"""
