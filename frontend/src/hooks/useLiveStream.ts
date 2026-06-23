import { useEffect, useRef } from 'react'

export function useLiveStream(onUpdate: () => void) {
  const cbRef = useRef(onUpdate)
  cbRef.current = onUpdate
  useEffect(() => {
    const es = new EventSource(`${import.meta.env.VITE_API_BASE ?? ''}/api/live/stream`)
    es.addEventListener('sim_update', () => cbRef.current())
    return () => es.close()
  }, [])
}
