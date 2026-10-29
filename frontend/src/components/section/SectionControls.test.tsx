// @vitest-environment jsdom
import { cleanup, fireEvent, render, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { useState } from 'react'
import SectionControls from './SectionControls'
import { createDefaultSectionParams } from './sectionDefaults'
import type { Plane, SectionParams } from '../../types'

const DIMS = { I: 4, J: 5, K: 3 }

function Controls({ testId }: { testId: string }) {
  const [params, setParams] = useState<SectionParams>(() => createDefaultSectionParams(DIMS, ['TEMP'], 'YZ'))
  return (
    <div data-testid={testId}>
      <SectionControls
        meta={{ variables: ['TEMP'] }}
        params={params}
        axisSize={4}
        axisCoordLabel="X"
        onPlaneChange={(plane: Plane) => setParams((p) => ({ ...p, plane }))}
        onChange={(patch) => setParams((p) => ({ ...p, ...patch }))}
      />
    </div>
  )
}

afterEach(cleanup)

describe('SectionControls を複数同時に表示したとき', () => {
  // タブの状態保持のため、断面ビュー・ディレクトリモード・比較タブの操作パネルは同時にマウントされている。
  // ラジオボタンの name が共通だとブラウザが1つのグループとして扱い、片方で選ぶともう片方の選択が外れていた
  it('一方で断面方向を選んでも、もう一方の選択は外れない', () => {
    const { getByTestId } = render(
      <>
        <Controls testId="first" />
        <Controls testId="second" />
      </>,
    )
    const first = within(getByTestId('first'))
    const second = within(getByTestId('second'))

    fireEvent.click(first.getByRole('radio', { name: 'XY' }))

    expect((first.getByRole('radio', { name: 'XY' }) as HTMLInputElement).checked).toBe(true)
    expect((second.getByRole('radio', { name: 'YZ' }) as HTMLInputElement).checked).toBe(true)
  })

  it('カラーマップの種類（プリセット / カスタム）も独立している', () => {
    const { getByTestId } = render(
      <>
        <Controls testId="first" />
        <Controls testId="second" />
      </>,
    )
    fireEvent.click(within(getByTestId('first')).getByRole('radio', { name: 'カスタム' }))
    expect((within(getByTestId('second')).getByRole('radio', { name: 'プリセット' }) as HTMLInputElement).checked).toBe(
      true,
    )
  })
})
