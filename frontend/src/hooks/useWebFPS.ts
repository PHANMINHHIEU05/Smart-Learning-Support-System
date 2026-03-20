/**
 * Custom React hook for measuring web/browser FPS.
 *
 * Measures frames drawn per second using requestAnimationFrame.
 * Updates FPS calculation every 1 second.
 */

import { useEffect, useState } from "react";

export function useWebFPS(): number {
  const [fps, setFps] = useState(0);

  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();
    let animationFrameId: number | null = null;

    const updateFPS = () => {
      frameCount++;
      const now = performance.now();

      // Update FPS every 1 second
      if (now >= lastTime + 1000) {
        const currentFPS = frameCount / ((now - lastTime) / 1000);
        setFps(Math.round(currentFPS * 10) / 10); // Round to 1 decimal place
        frameCount = 0;
        lastTime = now;
      }

      animationFrameId = requestAnimationFrame(updateFPS);
    };

    animationFrameId = requestAnimationFrame(updateFPS);

    return () => {
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, []);

  return fps;
}
