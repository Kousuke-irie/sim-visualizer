import { expect, test, type Page } from '@playwright/test'
import { createSimulationDir, plotTraces, recordApiRequests } from './fixtures'

// 2ケース比較（DESIGN_research_features.md §3）。B は TEMP だけ +1.5 ずらした合成ラン
async function openRun(page: Page, path: string) {
  await page.getByPlaceholder('例: /data/mecamamo').fill(path)
  await page.getByRole('button', { name: 'ディレクトリを開く' }).click()
  await expect(page.locator('.section-view__meta').getByText(path)).toBeVisible()
}

test.describe('比較タブ', () => {
  let runA: string
  let runB: string
  let otherGrid: string

  test.beforeAll(() => {
    runA = createSimulationDir({ name: 'run_a' })
    runB = createSimulationDir({ name: 'run_b', tempOffset: 1.5 })
    otherGrid = createSimulationDir({ name: 'run_small', ni: 3 })
  })

  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.locator('.app__navbar').getByText('ディレクトリモード', { exact: true }).click()
  })

  test('ランが1つだけなら、もう1つ開くよう案内する', async ({ page }) => {
    await openRun(page, runA)
    await page.getByText('比較', { exact: true }).click()
    await expect(page.getByText('比較するには、もう1つランを開いてください')).toBeVisible()
  })

  test('2つ開くと、B−A の差分を描く（海域は一様に +1.5、陸地は空白）', async ({ page }) => {
    await openRun(page, runA)
    await openRun(page, runB)

    await page.getByText('比較', { exact: true }).click()
    await expect(page.locator('.js-plotly-plot:visible')).toBeVisible()

    // 既定の変数は座標以外の先頭（U）なので TEMP を選び、陸地（i=0 の列）を含む XY 断面にする
    const controls = page.locator('.section-controls:visible')
    let responsePromise = page.waitForResponse('**/api/compare/section')
    await controls.locator('select').first().selectOption('TEMP')
    await responsePromise
    responsePromise = page.waitForResponse('**/api/compare/section')
    await controls.getByRole('radio', { name: 'XY' }).check({ force: true })
    await responsePromise

    const [fill] = await plotTraces(page)
    const z = (fill.z as (number | null)[][]).flat()
    expect(z.filter((v) => v !== null).every((v) => Math.abs((v as number) - 1.5) < 1e-6)).toBe(true)
    expect(z.some((v) => v === null)).toBe(true)
    await expect(page.getByText(/TEMP の差（B − A）: run_b − run_a/)).toBeVisible()
  })

  test('差分図でも、見た目の変更ではサーバーに問い合わせない', async ({ page }) => {
    await openRun(page, runA)
    await openRun(page, runB)
    const responsePromise = page.waitForResponse('**/api/compare/section')
    await page.getByText('比較', { exact: true }).click()
    await responsePromise
    await expect(page.locator('.js-plotly-plot:visible')).toBeVisible()

    const requests = recordApiRequests(page)
    await page.locator('.colormap-select__trigger:visible').click()
    await page.getByRole('option', { name: 'coolwarm' }).click()
    await page.waitForTimeout(500)
    expect(requests).toHaveLength(0)
  })

  test('格子の違うランを B に選ぶと、比較できない理由を表示する', async ({ page }) => {
    await openRun(page, runA)
    await openRun(page, runB)
    await openRun(page, otherGrid)
    await page.getByText('比較', { exact: true }).click()
    await page.locator('.compare-select select').nth(0).selectOption({ label: 'run_a' })
    await page.locator('.compare-select select').nth(1).selectOption({ label: 'run_small' })
    await expect(page.getByText(/格子寸法が異なるため比較できません: A=4x5x3 B=3x5x3/)).toBeVisible()
  })
})
