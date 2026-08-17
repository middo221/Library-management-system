import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/** Last line of defence: a render crash shows a way forward, not a white screen. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Unhandled render error', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div className="flex min-h-screen items-center justify-center bg-paper px-6">
        <div className="max-w-md text-center">
          <p className="font-display text-2xl font-semibold text-ink">Something came apart</p>
          <p className="mt-3 text-sm text-ink/60">
            The page could not be displayed. Reloading usually clears it; if it keeps happening,
            tell a librarian what you were doing.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-6 rounded-sm bg-shelf px-4 py-2.5 text-sm font-medium text-paper hover:bg-shelf/90"
          >
            Reload the page
          </button>
        </div>
      </div>
    )
  }
}
