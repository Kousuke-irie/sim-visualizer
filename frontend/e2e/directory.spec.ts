import { expect, test } from '@playwright/test'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { E2E_DATA_ROOT } from './dataRoot'
import { createSimulationDir } from './fixtures'

test.describe('ディレクトリモード', () => {
  let simDir: string

  test.beforeAll(() => {
    simDir = createSimulationDir()
  })

  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.getByText('ディレクトリモード', { exact: true }).first().click()
    await page.getByPlaceholder('例: /data/mecamamo').fill(simDir)
    await page.getByRole('button', { name: 'ディレクトリを開く' }).click()
    await expect(page.getByText('フレーム数 3')).toBeVisible()
  })

  test('時間スライダーでフレームを切り替えると、そのフレームのデータを取得して描画する', async ({ page }) => {
    await expect(page.locator('.js-plotly-plot:visible')).toBeVisible()

    const responsePromise = page.waitForResponse('**/api/directory/section/data')
    await page.locator('.time-slider input[type=range]').fill('2')
    const body = await (await responsePromise).json()

    expect(body.frame_index).toBe(2)
    expect(body.time_sec).toBe(7200)
    await expect(page.locator('.time-slider__value')).toContainText('3/3')
  })

  test('時系列タブで地点とパラメータを選んで深度別の時系列を表示する', async ({ page }) => {
    await page.getByText('時系列', { exact: true }).click()
    await expect(page.locator('.js-plotly-plot:visible')).toBeVisible()

    const responsePromise = page.waitForResponse('**/api/directory/timeseries/data')
    await page.locator('.point-param-select select').first().selectOption('TEMP')
    const response = await responsePromise
    expect(response.request().postDataJSON()).toMatchObject({ param: 'TEMP' })
  })

  test('時系列の地点を切り替えても、ユーザーが入力したタイトルは保持される', async ({ page }) => {
    await page.getByText('時系列', { exact: true }).click()
    const title = page.getByRole('textbox', { name: 'タイトル' })
    await title.fill('湾奥の溶存酸素')

    const responsePromise = page.waitForResponse('**/api/directory/timeseries/data')
    await page.locator('.point-param-select select').nth(1).selectOption('02')
    await responsePromise

    await expect(title).toHaveValue('湾奥の溶存酸素')
  })

  test('input.dat の無いディレクトリはエラーを表示する', async ({ page }) => {
    await page.getByPlaceholder('例: /data/mecamamo').fill(mkdtempSync(join(E2E_DATA_ROOT, 'empty-')))
    await page.getByRole('button', { name: 'ディレクトリを開く' }).click()
    await expect(page.getByText(/input.dat が見つかりません/)).toBeVisible()
  })

  test('データルートの外は開けない', async ({ page }) => {
    await page.getByPlaceholder('例: /data/mecamamo').fill('/')
    await page.getByRole('button', { name: 'ディレクトリを開く' }).click()
    await expect(page.getByText(/許可されたデータディレクトリの外/)).toBeVisible()
  })

  test('参照ダイアログはデータルートから始まり、それより上には戻れない', async ({ page }) => {
    // 入力欄にパスがあるとそこから開くため、空にして既定の起点を確認する
    await page.getByPlaceholder('例: /data/mecamamo').fill('')
    await page.getByRole('button', { name: '参照…' }).click()
    await expect(page.locator('.directory-browser__current')).toHaveText(E2E_DATA_ROOT)
    await expect(page.getByRole('button', { name: '↑ 上へ' })).toBeDisabled()
  })

  test('時系列の初回取得に失敗してもエラーを表示し、別のパラメータに切り替えられる', async ({ page }) => {
    const brokenDir = createSimulationDir()
    // 時系列タブが最初に開く DOX-01 を壊す
    writeFileSync(join(brokenDir, 'hist', 'DOX-01.dat'), 'broken\n')
    await page.getByPlaceholder('例: /data/mecamamo').fill(brokenDir)
    await page.getByRole('button', { name: 'ディレクトリを開く' }).click()
    await expect(page.getByText(brokenDir)).toBeVisible()

    await page.getByText('時系列', { exact: true }).click()
    await expect(page.locator('.error-banner')).toBeVisible()

    await page.locator('.point-param-select select').first().selectOption('TEMP')
    await expect(page.locator('.js-plotly-plot:visible')).toBeVisible()
  })
})
