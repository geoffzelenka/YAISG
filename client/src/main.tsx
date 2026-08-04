import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import { App } from './App'
import { ContentProvider } from './api/content'
import { AuthProvider } from './features/auth/AuthProvider'
import './index.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ContentProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </ContentProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
