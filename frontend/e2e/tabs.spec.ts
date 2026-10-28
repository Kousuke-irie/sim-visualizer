import { expect, test } from '@playwright/test'
import { join } from 'node:path'
import { createSimulationDir } from './fixtures'

// 以前はタブを切り替えると各ビューがアンマウントされ、アップロードや開いたディレクトリが消えていた（I-10）
test('タブを切り替えて戻っても、アップロードしたファイルと設定が残る', async ({ page }) => {
  const simDir = createSimulationDir()
  await page.goto('/')
  // 非表示のビューも DOM に残るので、見出しと区別するためタブはナビゲーションバーの中から選ぶ
  const tab = (name: string) => page.locator('.app__navbar').getByText(name, { exact: true })

  await page.locator('input[type=file][accept=".plt"]').setInputFiles(join(simDir, 'field2', 'tec-00000.plt'))
  await expect(page.getByText('格子 I=4 J=5 K=3')).toBeVisible()
  await page.locator('select:visible').first().selectOption('SAL')

  await tab('ディレクトリモード').click()
  await page.getByPlaceholder('例: /data/mecamamo').fill(simDir)
  await page.getByRole('button', { name: 'ディレクトリを開く' }).click()
  await expect(page.getByText('フレーム数 3')).toBeVisible()

  await tab('断面ビュー').click()
  await expect(page.getByText('格子 I=4 J=5 K=3')).toBeVisible()
  await expect(page.locator('select:visible').first()).toHaveValue('SAL')

  await tab('ディレクトリモード').click()
  await expect(page.getByText('フレーム数 3')).toBeVisible()
})
