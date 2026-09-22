import type { Session } from '@supabase/supabase-js'
import { createContext } from 'react'

export interface AuthContextValue {
  session: Session | null
  loading: boolean
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
