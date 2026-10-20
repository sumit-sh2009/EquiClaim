import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MotionConfig } from 'motion/react'
import { ThemeProvider } from 'next-themes'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { CurrencyProvider } from '@/context/CurrencyContext'
import App from './App.tsx'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {/* The room is dark by default; `disableTransitionOnChange` would fight
          the View Transitions wipe the toggle drives, so it stays off. */}
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} storageKey="equiclaim-theme">
        <MotionConfig reducedMotion="user">
          <TooltipProvider>
            <CurrencyProvider>
              <BrowserRouter>
                <App />
              </BrowserRouter>
              <Toaster closeButton position="bottom-right" />
            </CurrencyProvider>
          </TooltipProvider>
        </MotionConfig>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
