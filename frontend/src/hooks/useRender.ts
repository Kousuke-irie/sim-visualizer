import { useEffect, useRef, useState } from 'react'
import { fetchDirectorySectionData, fetchSectionData } from '../api/client'
import type { DirectorySectionDataRequest, DirectorySectionDataResponse, SectionDataRequest, SectionDataResponse } from '../types'

type SectionDataState = {
  data: SectionDataResponse | null
  loading: boolean
  error: string | null
}

// 表示スタイル（色・レベル数・ラベル等）は完全にクライアント側で処理するため、
// このフックは「平面・スライス位置・変数」が変わったときだけサーバーへ問い合わせる。
export function useSectionData(request: SectionDataRequest | null): SectionDataState {
  const [state, setState] = useState<SectionDataState>({ data: null, loading: false, error: null })
  const requestIdRef = useRef(0)
  const key = request ? JSON.stringify(request) : null

  useEffect(() => {
    if (!request) return
    const requestId = ++requestIdRef.current
    setState((prev) => ({ ...prev, loading: true, error: null }))

    fetchSectionData(request)
      .then((data) => {
        if (requestIdRef.current === requestId) {
          setState({ data, loading: false, error: null })
        }
      })
      .catch((err: Error) => {
        if (requestIdRef.current === requestId) {
          setState((prev) => ({ ...prev, loading: false, error: err.message }))
        }
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return state
}

type DirectorySectionDataState = {
  data: DirectorySectionDataResponse | null
  loading: boolean
  error: string | null
}

// ディレクトリモード版。平面・スライス位置・変数・フレームが変わったときだけサーバーへ問い合わせる。
export function useDirectorySectionData(request: DirectorySectionDataRequest | null): DirectorySectionDataState {
  const [state, setState] = useState<DirectorySectionDataState>({ data: null, loading: false, error: null })
  const requestIdRef = useRef(0)
  const key = request ? JSON.stringify(request) : null

  useEffect(() => {
    if (!request) return
    const requestId = ++requestIdRef.current
    setState((prev) => ({ ...prev, loading: true, error: null }))

    fetchDirectorySectionData(request)
      .then((data) => {
        if (requestIdRef.current === requestId) {
          setState({ data, loading: false, error: null })
        }
      })
      .catch((err: Error) => {
        if (requestIdRef.current === requestId) {
          setState((prev) => ({ ...prev, loading: false, error: err.message }))
        }
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return state
}
