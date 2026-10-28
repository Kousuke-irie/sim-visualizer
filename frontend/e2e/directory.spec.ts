import { expect, test } from '@playwright/test'
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
    await expect(page.locator('.js-plotly-plot')).toBeVisible()

    const responsePromise = page.waitForResponse('**/api/directory/section/data')
    await page.locator('.time-slider input[type=range]').fill('2')
    const body = await (await responsePromise).json()

    expect(body.frame_index).toBe(2)
    expect(body.time_sec).toBe(7200)
    await expect(page.locator('.time-slider__value')).toContainText('3/3')
  })

  test('時系列タブで地点とパラメータを選んで深度別の時系列を表示する', async ({ page }) => {
    await page.getByText('時系列', { exact: true }).click()
    await expect(page.locator('.js-plotly-plot')).toBeVisible()

    const responsePromise = page.waitForResponse('**/api/directory/timeseries/data')
    await page.locator('.point-param-select select').first().selectOption('TEMP')
    const response = await responsePromise
    expect(response.request().postDataJSON()).toMatchObject({ param: 'TEMP' })
  })

  test('input.dat の無いディレクトリはエラーを表示する', async ({ page }) => {
    await page.getByPlaceholder('例: /data/mecamamo').fill('/')
    await page.getByRole('button', { name: 'ディレクトリを開く' }).click()
    await expect(page.getByText(/input.dat が見つかりません/)).toBeVisible()
  })
})
