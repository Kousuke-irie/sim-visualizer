type Props = {
  message: string | null
  onDismiss?: () => void
}

export default function ErrorBanner({ message, onDismiss }: Props) {
  if (!message) return null
  return (
    <div className="error-banner" role="alert">
      <span className="error-banner__icon">!</span>
      <span className="error-banner__message">{message}</span>
      {onDismiss && (
        <button type="button" className="error-banner__dismiss" onClick={onDismiss} aria-label="閉じる">
          ×
        </button>
      )}
    </div>
  )
}
