import { describe, expect, it } from 'vitest'
import type { RunTemplate } from '../../types'
import { buildCreateRequest, formErrors, formatBytes, initialForm, isFortranNumber } from './newRunForm'

const TEMPLATE: RunTemplate = {
  base_dir: '/data/runs/case_v1',
  default_name: 'case_v2',
  default_compile_command: 'gfortran -O2 -o a.out mecnest.f90',
  input_lines: [
    { line_no: 4, tokens: ['0.8'], comment: 'dt', editable: true },
    { line_no: 8, tokens: ['3600.', '0.', '999999999999.'], comment: 'fifit2,5,6', editable: true },
    { line_no: 33, tokens: ['field2'], comment: '', editable: false },
  ],
  eco_constants: [
    { name: 'Iopt', value: '54.7', line_no: 3 },
    { name: 'aKp', value: '0.0106', line_no: 4 },
  ],
  copy_entries: [],
  excluded: [],
  copy_bytes: 0,
}

describe('buildCreateRequest', () => {
  it('変更した値だけを送る（元と同じ値に戻したものは送らない）', () => {
    const form = {
      ...initialForm(TEMPLATE),
      inputEdits: { 4: ['0.5'], 8: ['3600.', '0.', '999999999999.'] },
      ecoEdits: { Iopt: ' 60.0 ', aKp: '0.0106' },
    }
    expect(buildCreateRequest('d1', TEMPLATE, form)).toEqual({
      dir_id: 'd1',
      name: 'case_v2',
      compile_command: 'gfortran -O2 -o a.out mecnest.f90',
      input_edits: [{ line_no: 4, tokens: ['0.5'] }],
      eco_edits: [{ name: 'Iopt', value: '60.0' }],
    })
  })
})

describe('formErrors', () => {
  it('数値でない値・使えない名前を、送る前に一覧にする', () => {
    const errors = formErrors({
      ...initialForm(TEMPLATE),
      name: '../x',
      inputEdits: { 4: ['fast'] },
      ecoEdits: { Iopt: '1.0/' },
    })
    expect(errors).toHaveLength(3)
    expect(errors[0]).toContain('/')
    expect(errors[1]).toContain('4行目')
    expect(errors[2]).toContain('Iopt')
  })

  it('正しければ空', () => {
    expect(formErrors({ ...initialForm(TEMPLATE), ecoEdits: { Iopt: '6.0d1' } })).toEqual([])
  })
})

describe('isFortranNumber', () => {
  it.each(['1', '-2.5', '3600.', '.7d-1', '1.0e-6', '1.04167D-05'])('%s は数値', (t) => {
    expect(isFortranNumber(t)).toBe(true)
  })
  it.each(['', 'abc', '1.0.0', '../field2'])('%s は数値でない', (t) => {
    expect(isFortranNumber(t)).toBe(false)
  })
})

describe('formatBytes', () => {
  it('単位を付ける', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(609 * 1024)).toBe('609 KB')
    expect(formatBytes(738 * 1024 * 1024)).toBe('738.0 MB')
  })
})
