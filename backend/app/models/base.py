from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """API スキーマの共通基底。

    レスポンスでは既定値つきのフィールド（kind や vector_h=None など）も必ず送られるため、
    OpenAPI のレスポンス用スキーマでも required として出力する。こうしないと生成される TypeScript 型で
    optional（`kind?: 'plt'`）になり、実際の形とずれる。リクエスト用スキーマには影響しない。
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
