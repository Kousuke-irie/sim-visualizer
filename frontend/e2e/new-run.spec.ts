import { expect, test } from '@playwright/test'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { createSimulationDir } from './fixtures'

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

  test('値を変えて確認し、作成すると、隣に新しいランができる', async ({ page }) => {
    const nameInput = page.getByLabel('名前（元のランと同じ場所に作ります）')
    await expect(nameInput).toHaveValue('case_v2')

    const dtRow = page.locator('tr', { has: page.getByRole('cell', { name: 'dt', exact: true }) })
    await dtRow.locator('input').fill('0.5')
    await page.getByLabel('Iopt の新しい値').fill('60.0')
    await expect(page.getByText('変更した値: 2 個')).toBeVisible()

    const create = page.getByRole('button', { name: '作成' })
    await expect(create).toBeDisabled() // 確認する前は作成できない
    await page.getByRole('button', { name: '確認' }).click()
    await expect(page.getByText('54.7').last()).toBeVisible()
    await expect(page.locator('.new-run__changes li')).toHaveCount(2)

    await create.click()
    await expect(page.getByRole('status')).toContainText('新しいランを作成しました')

    const created = join(dirname(base), 'case_v2')
    expect(readFileSync(join(created, 'input.dat'), 'utf-8')).toMatch(/^0\.5\s+#dt$/m)
    expect(readFileSync(join(created, 'eco.h'), 'utf-8')).toContain('data Iopt/60.0/')
    expect(existsSync(join(created, 'simviz_run.json'))).toBe(true)
    expect(readFileSync(join(base, 'eco.h'), 'utf-8')).toContain('data Iopt/54.7/') // 元のランは変わらない
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
})
