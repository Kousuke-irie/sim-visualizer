import type { ReactNode } from 'react'

// 操作パネルの見出しつきグループ（断面・時系列の両方の操作パネルで使う）
export default function ControlGroup({
  icon,
  title,
  children,
}: {
  icon: ReactNode
  title: string
  children: ReactNode
}) {
  return (
    <div className="control-group">
      <div className="control-group__header">
        {icon}
        <span>{title}</span>
      </div>
      <div className="control-group__body">{children}</div>
    </div>
  )
}
