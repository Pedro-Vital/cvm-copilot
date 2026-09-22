import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AuthProvider } from '@/lib/auth-provider'
import { ChatEmpty } from '@/pages/chat/ChatEmpty'
import { ChatLayout } from '@/pages/chat/ChatLayout'
import { ChatThread } from '@/pages/chat/ChatThread'
import { SignIn } from '@/pages/SignIn'
import { SignUp } from '@/pages/SignUp'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<SignIn />} />
          <Route path="/signup" element={<SignUp />} />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<ChatEmpty />} />
            <Route path=":threadId" element={<ChatThread />} />
          </Route>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
