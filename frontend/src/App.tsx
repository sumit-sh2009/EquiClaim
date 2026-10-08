import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Suspense, lazy, useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { SiteFooter } from '@/components/site/SiteFooter'
import { SiteHeader } from '@/components/site/SiteHeader'
import { AcidCursor } from '@/components/ui/acid-cursor'
import { NoiseTexture } from '@/components/ui/noise-texture'
import { SpeederLoader } from '@/components/ui/speeder-loader'
import { LandingPage } from '@/pages/LandingPage'

// Route-level code splitting: the landing page is the fast first paint;
// app pages load on demand.
const LedgerPage = lazy(() =>
  import('@/pages/LedgerPage').then((m) => ({ default: m.LedgerPage })),
)
const UploadPage = lazy(() =>
  import('@/pages/UploadPage').then((m) => ({ default: m.UploadPage })),
)
const ClaimDetailPage = lazy(() =>
  import('@/pages/ClaimDetailPage').then((m) => ({ default: m.ClaimDetailPage })),
)

function PageFallback() {
  return (
    <div className="site-container py-16">
      <SpeederLoader label="Loading page" className="min-h-64" />
    </div>
  )
}

function HashScroll() {
  const { hash, pathname } = useLocation()
  const reduceMotion = useReducedMotion()

  useEffect(() => {
    if (!hash) return
    const id = decodeURIComponent(hash.slice(1))
    const target = document.getElementById(id)
    if (!target) return
    target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
  }, [hash, pathname, reduceMotion])

  return null
}

function App() {
  const location = useLocation()
  const reduceMotion = useReducedMotion()

  return (
    <div className="relative flex min-h-screen flex-col bg-background">
      <HashScroll />
      <NoiseTexture className="fixed inset-0 z-[1] opacity-[0.03]" />
      <AcidCursor />
      <SiteHeader />
      <main id="main-content" className="flex-1">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={location.pathname}
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={{ duration: 0.15, ease: [0.2, 0.6, 0.2, 1] }}
          >
            <Suspense fallback={<PageFallback />}>
              <Routes location={location}>
                <Route path="/" element={<LandingPage />} />
                <Route path="/claims" element={<LedgerPage />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/claims/:claimId" element={<ClaimDetailPage />} />
              </Routes>
            </Suspense>
          </motion.div>
        </AnimatePresence>
      </main>
      <SiteFooter />
    </div>
  )
}

export default App
