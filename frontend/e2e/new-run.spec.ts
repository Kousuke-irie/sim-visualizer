import { expect, test, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { createSimulationDir } from './fixtures'

// 待ち行列は E2E 全体で共有なので、そのテストで作ったランの行を、ランのパスで探す
function jobItem(page: Page, runDir: string) {
  return page.locator(`.jobs__item[data-run-dir="${runDir}"]`)
}

// 新しいランの作成（DESIGN_research_features.md §4）。ブラウザ → バックエンド → 本物の runner → ディスク まで通す
test.describe('新しいラン', () => {
  let base: string

  test.beforeEach(async ({ page }) => {
    base = createSimulationDir({ name: 'case_v1', modelFiles: true })
    await page.goto('/')
    await page.locator('.app__navbar').getByText('ディレクトリモード', { exact: true }).click()
    await page.getByPlaceholder('例: /data/mecamamo').fill(base)
    await page.getByRole('button', { name: 'ディレクトリを開く' }).click()
    await expect(page.locator('.section-view__meta').getByText(base)).toBeVisible()
    await page.getByText('新しいラン', { exact: true }).click()
    await expect(page.getByRole('heading', { name: 'input.dat の値' })).toBeVisible()
  })

  test('値を変えて確認し、作成して実行すると、隣に新しいランができて計算が終わる', async ({ page }) => {
    const nameInput = page.getByLabel('名前（元のランと同じ場所に作ります）')
    await expect(nameInput).toHaveValue('case_v2')

    const dtRow = page.locator('tr', { has: page.getByRole('cell', { name: 'dt', exact: true }) })
    await dtRow.locator('input').fill('0.5')
    await page.getByLabel('Iopt の新しい値').fill('60.0')
    await expect(page.getByText('変更した値: 2 個')).toBeVisible()

    const create = page.getByRole('button', { name: '作成して実行' })
    await expect(create).toBeDisabled() // 確認する前は作成できない
    await page.getByRole('button', { name: '確認' }).click()
    await expect(page.getByText('54.7').last()).toBeVisible()
    await expect(page.locator('.new-run__changes li')).toHaveCount(2)

    await create.click()
    await expect(page.getByRole('status')).toContainText('新しいランを作成しました')
    await expect(page.getByRole('status')).toContainText('待ち行列に入れました')

    const created = join(dirname(base), 'case_v2')
    expect(readFileSync(join(created, 'input.dat'), 'utf-8')).toMatch(/^0\.5\s+#dt$/m)
    expect(readFileSync(join(created, 'eco.h'), 'utf-8')).toContain('data Iopt/60.0/')
    expect(readFileSync(join(base, 'eco.h'), 'utf-8')).toContain('data Iopt/54.7/') // 元のランは変わらない

    // 偽の gfortran でコンパイルし、偽のモデルが 2 枚の tec-*.plt を書き出すまで待つ（一覧は数秒おきに更新される）
    const job = jobItem(page, created)
    await expect(job.locator('.jobs__status')).toHaveText('完了', { timeout: 20_000 })
    await expect(job).toContainText('出力 2 / 2 フレーム')
    const record = JSON.parse(readFileSync(join(created, 'simviz_run.json'), 'utf-8'))
    expect(record).toMatchObject({ status: 'succeeded', exit_code: 0, gfortran_version: 'GNU Fortran (fake) 0.0' })

    await job.locator('summary').click()
    await expect(job.locator('pre')).toContainText('fake model: done')

    // 完了したランは、元のランとそのまま比較できる
    await job.getByRole('button', { name: '元のランと比較' }).click()
    await expect(page.getByRole('radio', { name: '差分（B − A）' })).toBeChecked()
    await expect(page.locator('.js-plotly-plot:visible')).toBeVisible()
  })

  test('実行中の計算は中止でき、途中までの出力は残る', async ({ page }) => {
    await page.getByLabel('名前（元のランと同じ場所に作ります）').fill('case_slow')
    // 予定のフレーム数を増やして、中止する時間をつくる（endtime 7200 → 72000、0.5 秒ごとに 1 枚で 10 秒かかる）
    const endtimeRow = page.locator('tr', { has: page.getByRole('cell', { name: 'endtime,ntime,irst', exact: true }) })
    await endtimeRow.locator('input').first().fill('72000.')
    await page.getByRole('button', { name: '確認' }).click()
    await page.getByRole('button', { name: '作成して実行' }).click()

    const job = jobItem(page, join(dirname(base), 'case_slow'))
    await expect(job.locator('.jobs__status')).toHaveText('計算中', { timeout: 15_000 })
    await expect(job).toContainText(/出力 \d+ \/ 20 フレーム/)
    page.once('dialog', (dialog) => dialog.accept())
    await job.getByRole('button', { name: '中止' }).click()
    await expect(job.locator('.jobs__status')).toHaveText('中止', { timeout: 15_000 })
    await expect(job.getByRole('button', { name: '開く' })).toBeVisible() // 途中までの出力は見られる
  })

  test('数値でない値は、送る前に指摘してボタンを押せなくする', async ({ page }) => {
    await page.getByLabel('Iopt の新しい値').fill('fast')
    await expect(page.getByText(/eco.h Iopt: Fortran の数値として正しくありません/)).toBeVisible()
    await expect(page.getByRole('button', { name: '確認' })).toBeDisabled()
  })

  test('出力先の行（field2 など）は入力欄にならない', async ({ page }) => {
    const field2Row = page.locator('tr', { has: page.getByRole('cell', { name: 'field2', exact: true }) })
    await expect(field2Row).toBeVisible()
    await expect(field2Row.locator('input')).toHaveCount(0)
  })

  test('格子寸法と地点の値は変更できず、hist の出力間隔は変更できる', async ({ page }) => {
    const row = (comment: string) => page.locator('tr', { has: page.getByRole('cell', { name: comment, exact: true }) })
    await expect(row('in,jn,kn,nest').locator('input')).toHaveCount(0)
    await expect(row('ijhist0').locator('input')).toHaveCount(0)
    // nhist,histout の行は histout だけが入力欄
    await expect(row('nhist,histout').locator('input')).toHaveCount(1)
    await expect(row('nhist,histout').locator('input')).toHaveValue('300.0')
  })
})
