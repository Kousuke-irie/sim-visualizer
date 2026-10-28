import { useEffect, useRef, useState } from 'react'

export type RequestState<Res> = {
  data: Res | null
  loading: boolean
  error: string | null
}

// 「リクエストの内容が変わったときだけサーバーに問い合わせ、最新の応答だけを採用する」共通フック。
// 表示スタイルはリクエストに含めない設計なので、見た目の変更では request の内容が変わらず通信も起きない。
// - request は再描画のたびに作り直されてよい。内容（JSON）が同じなら取り直さない
// - 遅れて返った古い応答は捨てる（スライダーを素早く動かしたときに表示が巻き戻らないように）
// - 失敗しても直前のデータは表示し続け、エラーだけを出す
export function useLatestRequest<Req, Res>(
  request: Req | null,
  fetcher: (req: Req) => Promise<Res>,
): RequestState<Res> {
  const [state, setState] = useState<RequestState<Res>>({ data: null, loading: false, error: null })
  const latestId = useRef(0)
  // fetcher はインライン関数で渡されることが多い。依存に入れると毎回取り直してしまうので最新値を ref で持つ
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher
  const key = request === null ? null : JSON.stringify(request)

  useEffect(() => {
    if (key === null) return
    const requestId = ++latestId.current
    setState((prev) => ({ ...prev, loading: true, error: null }))

    fetcherRef
      .current(JSON.parse(key) as Req)
      .then((data) => {
        if (latestId.current === requestId) setState({ data, loading: false, error: null })
      })
      .catch((err: Error) => {
        if (latestId.current === requestId) setState((prev) => ({ ...prev, loading: false, error: err.message }))
      })
  }, [key])

  return state
}
