import { useMemo, useState } from 'react'
import {
  buildCreateRequest,
  formErrors,
  formatBytes,
  initialForm,
  isEcoChanged,
  isFortranNumber,
  isInputLineChanged,
  type NewRunForm,
} from './newRunForm'
import ErrorBanner from '../common/ErrorBanner'
import { createRun, fetchRunTemplate, previewRun } from '../../api/client'
import { useLatestRequest } from '../../hooks/useLatestRequest'
import type { CreatedRun, DirectoryMeta, RunPreview, RunTemplate } from '../../types'

type Props = { meta: DirectoryMeta }

// ディレクトリモードの「新しいラン」タブ。表示中のランを元に、input.dat と eco.h の値を変えた新しいランを作る
// （DESIGN_research_features.md §4.1）。作成はホストの runner が行い、計算の実行は R5 で追加する
export default function NewRunPanel({ meta }: Props) {
  const request = useMemo(() => ({ dir_id: meta.dir_id }), [meta.dir_id])
  const { data: template, loading, error } = useLatestRequest(request, fetchRunTemplate)

  return (
    <>
      <ErrorBanner message={error} />
      {loading && !template && <div className="plot-placeholder compare-hint">元のランを読み込んでいます…</div>}
      {template && <NewRunEditor key={template.base_dir} dirId={meta.dir_id} template={template} />}
    </>
  )
}

function NewRunEditor({ dirId, template }: { dirId: string; template: RunTemplate }) {
  const [form, setForm] = useState<NewRunForm>(() => initialForm(template))
  const [ecoFilter, setEcoFilter] = useState('')
  const [preview, setPreview] = useState<RunPreview | null>(null)
  const [created, setCreated] = useState<CreatedRun | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const errors = formErrors(form)

  function update(patch: Partial<NewRunForm>) {
    setForm((prev) => ({ ...prev, ...patch }))
    // 値を変えたら前回の確認結果は古くなるので、もう一度確認してもらう
    setPreview(null)
    setCreated(null)
  }

  function setInputToken(lineNo: number, index: number, value: string) {
    const line = template.input_lines.find((l) => l.line_no === lineNo)
    if (!line) return
    const tokens = [...(form.inputEdits[lineNo] ?? line.tokens)]
    tokens[index] = value
    update({ inputEdits: { ...form.inputEdits, [lineNo]: tokens } })
  }

  async function run<T>(action: () => Promise<T>, onDone: (result: T) => void) {
    setBusy(true)
    setError(null)
    try {
      onDone(await action())
    } catch (err) {
      setError(err instanceof Error ? err.message : '失敗しました')
    } finally {
      setBusy(false)
    }
  }

  const request = buildCreateRequest(dirId, template, form)
  const changedCount = request.input_edits.length + request.eco_edits.length
  const filteredEco = template.eco_constants.filter((c) => c.name.toLowerCase().includes(ecoFilter.toLowerCase()))

  return (
    <div className="new-run">
      <section className="time-slider-card new-run__section">
        <h3>新しいラン</h3>
        <div className="new-run__row">
          <label className="text-field">
            <span>名前（元のランと同じ場所に作ります）</span>
            <input type="text" value={form.name} onChange={(e) => update({ name: e.target.value })} />
          </label>
          <label className="text-field new-run__wide">
            <span>コンパイルコマンド</span>
            <input
              type="text"
              value={form.compileCommand}
              onChange={(e) => update({ compileCommand: e.target.value })}
            />
          </label>
        </div>
        <p className="new-run__note">
          元のラン: {template.base_dir}（コピーするのは入力とソースの {formatBytes(template.copy_bytes)}
          。出力はコピーせず空のフォルダを作ります）
        </p>
      </section>

      <section className="time-slider-card new-run__section">
        <h3>input.dat の値</h3>
        <p className="new-run__note">
          数値の行だけ変更できます。ファイル名や出力先の行は、計算が新しいランの外へ書き出さないよう変更できません。
        </p>
        <table className="new-run__table">
          <thead>
            <tr>
              <th>行</th>
              <th>説明（元ファイルのコメント）</th>
              <th>値</th>
            </tr>
          </thead>
          <tbody>
            {template.input_lines.map((line) => {
              const tokens = form.inputEdits[line.line_no] ?? line.tokens
              return (
                <tr
                  key={line.line_no}
                  className={isInputLineChanged(template, form, line.line_no) ? 'is-changed' : ''}
                  data-line={line.line_no}
                >
                  <td>{line.line_no}</td>
                  <td>{line.comment}</td>
                  <td className="new-run__tokens">
                    {line.editable
                      ? tokens.map((t, i) => (
                          <input
                            key={i}
                            type="text"
                            aria-label={`${line.line_no}行目の${i + 1}番目の値`}
                            className={isFortranNumber(t) ? '' : 'is-invalid'}
                            value={t}
                            size={Math.max(4, t.length + 1)}
                            onChange={(e) => setInputToken(line.line_no, i, e.target.value)}
                          />
                        ))
                      : line.tokens.join(' ')}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>

      <section className="time-slider-card new-run__section">
        <h3>eco.h の定数（変更すると再コンパイルされます）</h3>
        <label className="text-field">
          <span>名前で絞り込む</span>
          <input type="text" value={ecoFilter} onChange={(e) => setEcoFilter(e.target.value)} placeholder="例: Alp" />
        </label>
        <table className="new-run__table">
          <thead>
            <tr>
              <th>名前</th>
              <th>元の値</th>
              <th>新しい値</th>
            </tr>
          </thead>
          <tbody>
            {filteredEco.map((c) => {
              const value = form.ecoEdits[c.name] ?? c.value
              return (
                <tr key={c.name} className={isEcoChanged(template, form, c.name) ? 'is-changed' : ''}>
                  <td>{c.name}</td>
                  <td>{c.value}</td>
                  <td>
                    <input
                      type="text"
                      aria-label={`${c.name} の新しい値`}
                      className={isFortranNumber(value) ? '' : 'is-invalid'}
                      value={value}
                      onChange={(e) => update({ ecoEdits: { ...form.ecoEdits, [c.name]: e.target.value } })}
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>

      <section className="time-slider-card new-run__section">
        {errors.map((e) => (
          <ErrorBanner key={e} message={e} />
        ))}
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
        <div className="new-run__actions">
          <span>変更した値: {changedCount} 個</span>
          <button
            type="button"
            className="btn-secondary"
            disabled={busy || errors.length > 0}
            onClick={() => run(() => previewRun(request), setPreview)}
          >
            確認
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={busy || errors.length > 0 || !preview || !!created}
            title={preview ? undefined : '先に「確認」で内容を確かめてください'}
            onClick={() => run(() => createRun(request), setCreated)}
          >
            作成
          </button>
        </div>

        {preview && (
          <div className="new-run__preview">
            <p>
              作成先: <code>{preview.target_dir}</code>（{preview.copy_count} ファイル・
              {formatBytes(preview.copy_bytes)}
              をコピー）
            </p>
            {preview.changes.length === 0 ? (
              <p>値の変更はありません（元のランと同じ設定で作ります）</p>
            ) : (
              <ul className="new-run__changes">
                {preview.changes.map((c) => (
                  <li key={`${c.file}-${c.where}`}>
                    {c.file} {c.where}: <code>{c.before}</code> → <code>{c.after}</code>
                  </li>
                ))}
              </ul>
            )}
            <details>
              <summary>コピーしないもの（{preview.excluded.length} 件）</summary>
              <ul>
                {preview.excluded.map((e) => (
                  <li key={e.path}>
                    {e.path} — {e.reason}
                  </li>
                ))}
              </ul>
            </details>
          </div>
        )}

        {created && (
          <div className="new-run__created" role="status">
            新しいランを作成しました: <code>{created.path}</code>
            <br />
            変更の記録は simviz_run.json に残しています。計算の実行（コンパイル・待ち行列）は次の段階で追加します。
          </div>
        )}
      </section>
    </div>
  )
}
