// 新しいランの作成フォームの状態から、サーバーに送る指定（変更した値だけ）を組み立てる純粋関数。
import type { CreateRunRequest, RunTemplate } from '../../types'

export type NewRunForm = {
  name: string
  compileCommand: string
  inputEdits: Record<number, string[]> // 行番号 → 値（編集した行だけ）
  ecoEdits: Record<string, string> // 定数名 → 値（編集したものだけ）
}

// Fortran の数値表記（runner 側の検査と同じ。入力中に赤く示すために使う）
const FORTRAN_NUMBER_RE = /^[+-]?(\d+\.?\d*|\.\d+)([dDeE][+-]?\d+)?$/

export function isFortranNumber(token: string): boolean {
  return FORTRAN_NUMBER_RE.test(token.trim())
}

export function initialForm(template: RunTemplate): NewRunForm {
  return { name: template.default_name, compileCommand: template.default_compile_command, inputEdits: {}, ecoEdits: {} }
}

export function isInputLineChanged(template: RunTemplate, form: NewRunForm, lineNo: number): boolean {
  const edited = form.inputEdits[lineNo]
  const original = template.input_lines.find((l) => l.line_no === lineNo)?.tokens
  return !!edited && !!original && edited.some((t, i) => t.trim() !== original[i])
}

export function isEcoChanged(template: RunTemplate, form: NewRunForm, name: string): boolean {
  const edited = form.ecoEdits[name]
  const original = template.eco_constants.find((c) => c.name === name)?.value
  return edited !== undefined && edited.trim() !== original
}

// 入力に誤りがあれば、その一覧（無ければ空）。送る前に画面で気づけるようにする
export function formErrors(form: NewRunForm): string[] {
  const errors: string[] = []
  if (!form.name.trim()) errors.push('名前を入力してください')
  if (/[/\\]/.test(form.name) || form.name.startsWith('.')) errors.push('名前に / や先頭の . は使えません')
  for (const [lineNo, tokens] of Object.entries(form.inputEdits)) {
    const bad = tokens.filter((t) => !isFortranNumber(t))
    if (bad.length > 0) errors.push(`input.dat ${lineNo}行目: 数値でない値 ${bad.join(', ')}`)
  }
  for (const [name, value] of Object.entries(form.ecoEdits)) {
    if (!isFortranNumber(value)) errors.push(`eco.h ${name}: Fortran の数値として正しくありません（${value}）`)
  }
  return errors
}

export function buildCreateRequest(dirId: string, template: RunTemplate, form: NewRunForm): CreateRunRequest {
  return {
    dir_id: dirId,
    name: form.name.trim(),
    compile_command: form.compileCommand.trim(),
    input_edits: Object.entries(form.inputEdits)
      .filter(([lineNo]) => isInputLineChanged(template, form, Number(lineNo)))
      .map(([lineNo, tokens]) => ({ line_no: Number(lineNo), tokens: tokens.map((t) => t.trim()) })),
    eco_edits: Object.entries(form.ecoEdits)
      .filter(([name]) => isEcoChanged(template, form, name))
      .map(([name, value]) => ({ name, value: value.trim() })),
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
