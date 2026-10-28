import { expect, test } from '@playwright/test'
import { join } from 'node:path'
import { createSimulationDir, plotTraces, recordApiRequests } from './fixtures'

const DEBOUNCE_MARGIN_MS = 500

test.describe('断面ビュー', () => {
  let pltPath: string

  test.beforeAll(() => {
    pltPath = join(createSimulationDir(), 'field2', 'tec-00000.plt')
  })

  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.locator('input[type=file][accept=".plt"]').setInputFiles(pltPath)
    await expect(page.getByText('格子 I=4 J=5 K=3')).toBeVisible()
    await expect(page.locator('.js-plotly-plot')).toBeVisible()
  })

  test('アップロードした .plt の断面がコンター図として描画される', async ({ page }) => {
    const traces = await plotTraces(page)
    expect(traces[0].type).toBe('contour')
    await expect(page.getByText(/値範囲/)).toBeVisible()
  })

  test('見た目のパラメータ変更はサーバーに問い合わせず、ブラウザ内だけで再描画される', async ({ page }) => {
    const requests = recordApiRequests(page)
    const before = (await plotTraces(page))[0].colorscale

    await page.locator('.colormap-select__trigger').click()
    await page.getByRole('option', { name: 'plasma' }).click()
    await page.waitForTimeout(DEBOUNCE_MARGIN_MS)

    const after = (await plotTraces(page))[0].colorscale
    expect(after).not.toEqual(before)
    expect(requests).toHaveLength(0)
  })

  test('描画変数の変更はサーバーからデータを取り直す', async ({ page }) => {
    const responsePromise = page.waitForResponse('**/api/section/data')
    await page.locator('select').first().selectOption('SAL')
    const response = await responsePromise

    expect(response.request().postDataJSON()).toMatchObject({ variable: 'SAL' })
    await expect(page.getByText(/SAL 分布/)).toBeVisible()
  })

  test('断面方向を切り替えると縦軸が Y になる', async ({ page }) => {
    await page.getByRole('radio', { name: 'XY' }).check({ force: true })
    await expect(page.getByText(/XY断面/)).toBeVisible()
  })
})
