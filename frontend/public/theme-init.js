// Resolve the stored theme before first paint so the room never flashes
// daylight on load. next-themes takes over on mount using the same key.
try {
  var stored = localStorage.getItem('equiclaim-theme')
  if (stored === 'dark') document.documentElement.classList.add('dark')
} catch (e) {}
