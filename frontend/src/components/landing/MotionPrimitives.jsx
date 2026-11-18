import { useEffect, useRef, useState } from "react";

/**
 * Detects whether the user has requested reduced motion.
 */
export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) {
      return false;
    }
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) {
      return undefined;
    }
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleChange = (event) => setReduced(event.matches);

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  return reduced;
}

/**
 * Scroll-triggered entrance wrapper using IntersectionObserver and GPU transforms.
 */
export function Reveal({
  children,
  className = "",
  delayMs = 0,
  direction = "up",
  threshold = 0.12,
}) {
  const ref = useRef(null);
  const prefersReducedMotion = usePrefersReducedMotion();
  const [isVisible, setIsVisible] = useState(prefersReducedMotion);

  useEffect(() => {
    if (prefersReducedMotion) {
      setIsVisible(true);
      return undefined;
    }

    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      setIsVisible(true);
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold, rootMargin: "0px 0px -40px 0px" }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [prefersReducedMotion, threshold]);

  const hiddenTransform =
    direction === "left"
      ? "-translate-x-5"
      : direction === "right"
      ? "translate-x-5"
      : direction === "scale"
      ? "scale-95"
      : "translate-y-6";

  return (
    <div
      ref={ref}
      style={
        !prefersReducedMotion && delayMs > 0
          ? { transitionDelay: `${delayMs}ms` }
          : undefined
      }
      className={`transition-all duration-700 ease-out will-change-transform ${
        isVisible
          ? "translate-x-0 translate-y-0 scale-100 opacity-100"
          : `${hiddenTransform} opacity-0`
      } ${className}`.trim()}
    >
      {children}
    </div>
  );
}

/**
 * Smoothly animates an integer/float value for illustrative demo telemetry.
 */
export function AnimatedNumber({ value = 0, durationMs = 700, suffix = "" }) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const [displayValue, setDisplayValue] = useState(value);
  const previousValueRef = useRef(value);

  useEffect(() => {
    if (prefersReducedMotion) {
      setDisplayValue(value);
      previousValueRef.current = value;
      return undefined;
    }

    const startValue = previousValueRef.current;
    const delta = value - startValue;
    if (delta === 0) {
      return undefined;
    }

    let animationFrameId = null;
    const startTime = performance.now();

    const step = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / durationMs);
      // Cubic ease-out
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startValue + delta * eased);
      setDisplayValue(current);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step);
      } else {
        previousValueRef.current = value;
      }
    };

    animationFrameId = requestAnimationFrame(step);
    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [value, durationMs, prefersReducedMotion]);

  return (
    <span className="font-mono tabular-nums">
      {displayValue}
      {suffix}
    </span>
  );
}


export function AnimatedBar({ value = 0, className = "", trackClassName = "", durationMs = 900 }) {
  const ref = useRef(null);
  const prefersReducedMotion = usePrefersReducedMotion();
  const [width, setWidth] = useState(prefersReducedMotion ? value : 0);

  useEffect(() => {
    if (prefersReducedMotion) {
      setWidth(value);
      return undefined;
    }
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      setWidth(value);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setWidth(value);
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [value, prefersReducedMotion]);

  return (
    <div
      ref={ref}
      role="presentation"
      className={`h-2 w-full overflow-hidden rounded-full ${trackClassName}`.trim()}
    >
      <div
        style={{ width: `${width}%`, transitionDuration: `${durationMs}ms` }}
        className={`h-full rounded-full transition-[width] ease-out ${className}`.trim()}
      />
    </div>
  );
}
