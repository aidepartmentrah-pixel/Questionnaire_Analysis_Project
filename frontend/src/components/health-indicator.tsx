import { useEffect, useState } from 'react'

import { getHealth } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type Status = 'checking' | 'online' | 'offline'

const STATUS_CONFIG: Record<
  Status,
  { label: string; dotClassName: string; variant: 'outline' | 'success' | 'destructive' }
> = {
  checking: { label: 'Checking backend…', dotClassName: 'bg-muted-foreground', variant: 'outline' },
  online: { label: 'Backend connected', dotClassName: 'bg-success', variant: 'success' },
  offline: { label: 'Backend unreachable', dotClassName: 'bg-destructive', variant: 'destructive' },
}

export function HealthIndicator() {
  const [status, setStatus] = useState<Status>('checking')

  useEffect(() => {
    const controller = new AbortController()

    getHealth(controller.signal)
      .then(() => setStatus('online'))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setStatus('offline')
      })

    return () => controller.abort()
  }, [])

  const config = STATUS_CONFIG[status]

  return (
    <div role="status" aria-live="polite">
      <Badge variant={config.variant} className="gap-1.5 py-1">
        <span className={cn('h-1.5 w-1.5 rounded-full', config.dotClassName)} aria-hidden="true" />
        {config.label}
      </Badge>
    </div>
  )
}
