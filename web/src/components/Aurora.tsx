import { useCallback, useEffect, useRef } from "react";

export default function Aurora() {
  const glowRef = useRef<HTMLDivElement>(null);
  const posRef = useRef({ x: -200, y: -200 });
  const rafRef = useRef(0);

  const onMove = useCallback((e: MouseEvent) => {
    posRef.current = { x: e.clientX, y: e.clientY };
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(() => {
        if (glowRef.current) {
          glowRef.current.style.transform = `translate(${posRef.current.x}px, ${posRef.current.y}px) translate(-50%, -50%)`;
        }
        rafRef.current = 0;
      });
    }
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", onMove);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [onMove]);

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div className="aurora-blob aurora-1" />
      <div className="aurora-blob aurora-2" />
      <div className="aurora-blob aurora-3" />
      <div ref={glowRef} className="aurora-cursor" />
    </div>
  );
}
