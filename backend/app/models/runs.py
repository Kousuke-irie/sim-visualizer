"""新しいランの作成（DESIGN_research_features.md §4）の API スキーマ。runner とバックエンドで共通に使う。"""

from typing import Literal

from app.models.base import ApiModel


class InputLineModel(ApiModel):
    line_no: int
    tokens: list[str]
    comment: str
    editable: bool  # 数値だけの行。ファイル名・出力先の行は編集できない


class EcoConstantModel(ApiModel):
    name: str
    value: str
    line_no: int


class CopyEntry(ApiModel):
    path: str  # 元ランからの相対パス
    bytes: int
    is_dir: bool


class ExcludedEntry(ApiModel):
    path: str
    reason: str


class InputEdit(ApiModel):
    line_no: int
    tokens: list[str]


class EcoEdit(ApiModel):
    name: str
    value: str


class NewRunSpec(ApiModel):
    name: str
    input_edits: list[InputEdit] = []
    eco_edits: list[EcoEdit] = []
    compile_command: str


class RunChange(ApiModel):
    file: Literal["input.dat", "eco.h"]
    where: str  # 「8行目（#fifit2,5,6）」や定数名
    before: str
    after: str


class RunTemplate(ApiModel):
    base_dir: str
    default_name: str
    default_compile_command: str
    input_lines: list[InputLineModel]
    eco_constants: list[EcoConstantModel]
    copy_entries: list[CopyEntry]
    excluded: list[ExcludedEntry]
    copy_bytes: int


class RunPreview(ApiModel):
    target_dir: str
    changes: list[RunChange]
    copy_count: int
    copy_bytes: int
    excluded: list[ExcludedEntry]


class CreatedRun(ApiModel):
    path: str
    changes: list[RunChange]
    record_file: str


# ---- バックエンド（/api/runs/*）用：ランは開いたディレクトリの dir_id で指定する ----


class RunTemplateRequest(ApiModel):
    dir_id: str


class CreateRunRequest(NewRunSpec):
    dir_id: str


# ---- runner（ホスト）用：ランはホスト上のパスで指定する ----


class RunnerTemplateRequest(ApiModel):
    base_dir: str


class RunnerCreateRequest(NewRunSpec):
    base_dir: str
