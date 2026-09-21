import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { ApiError, api } from '@/lib/api'
import { supabase } from '@/lib/supabase'

interface CurrentUser {
  id: string
  email: string | null
}

export function Home() {
  const [me, setMe] = useState<CurrentUser | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<CurrentUser>('/auth/me')
      .then(setMe)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Unknown error')
      })
  }, [])

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 p-4">
      <h1 className="text-xl font-medium">CVM Copilot</h1>
      {me && (
        <p className="text-sm text-muted-foreground">
          Signed in as {me.email ?? me.id} — verified by the backend.
        </p>
      )}
      {error && <p className="text-sm text-destructive">Backend check failed: {error}</p>}
      <Button variant="outline" onClick={() => supabase.auth.signOut()}>
        Sign out
      </Button>
    </div>
  )
}
