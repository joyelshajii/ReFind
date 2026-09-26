"use client";

import { useEffect, useRef } from "react";

interface Star3D {
  x: number;       // 3D coordinate (-width to +width)
  y: number;       // 3D coordinate (-height to +height)
  z: number;       // Depth (e.g. 50 to 1200)
  baseZ: number;   // Initial depth
  vx: number;      // Continuous drift velocity X
  vy: number;      // Continuous drift velocity Y
  vz: number;      // Continuous forward drift velocity Z
  size: number;    // Intrinsic size
  brightness: number; // Intrinsic luminosity
  history: { x: number; y: number }[]; // Trail for motion streaks
}

export default function GravitationalField() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Responsive star count
    const isMobile = width < 640;
    const isTablet = width >= 640 && width < 1024;
    const starCount = isMobile ? 450 : isTablet ? 750 : 1100;

    // Virtual 3D camera
    const camera = {
      x: 0,
      y: 0,
      targetX: 0,
      targetY: 0,
      fov: 480, // Projection focal length
    };

    // Central input rectangle bounding box in screen pixels
    let inputRect = {
      cx: width / 2,
      cy: height * 0.44,
      halfW: Math.min(width * 0.42, 360),
      halfH: 38,
      radius: 38, // Fully rounded pill ends
    };

    const updateInputRect = () => {
      // Find the search input form element with data-grav-input
      const el = document.querySelector("[data-grav-input]") || document.querySelector("form");
      if (el) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          inputRect = {
            cx: rect.left + rect.width / 2,
            cy: rect.top + rect.height / 2,
            halfW: rect.width / 2,
            halfH: rect.height / 2,
            radius: Math.min(rect.height / 2, 38),
          };
          return;
        }
      }
      inputRect = {
        cx: width / 2,
        cy: height * 0.44,
        halfW: Math.min(width * 0.42, 360),
        halfH: 38,
        radius: 38,
      };
    };

    updateInputRect();

    // Initialize 3D Stars in a cylindrical/cuboid volume
    const stars: Star3D[] = [];
    for (let i = 0; i < starCount; i++) {
      const z = 80 + Math.random() * 1100;
      stars.push({
        x: (Math.random() - 0.5) * width * 2.8,
        y: (Math.random() - 0.5) * height * 2.8,
        z,
        baseZ: z,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.18,
        vz: 0.15 + Math.random() * 0.4, // Gentle forward flow through space
        size: Math.random() < 0.08 ? 1.6 + Math.random() * 1.4 : 0.7 + Math.random() * 0.9,
        brightness: Math.random() < 0.1 ? 0.85 + Math.random() * 0.15 : 0.25 + Math.random() * 0.55,
        history: [],
      });
    }

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      updateInputRect();
    };

    const handleMouseMove = (e: MouseEvent) => {
      // Normalize mouse to [-1, 1] relative to viewport center
      const normX = (e.clientX - width / 2) / (width / 2);
      const normY = (e.clientY - height / 2) / (height / 2);

      // Smooth camera pan angle in 3D world space
      camera.targetX = normX * 120;
      camera.targetY = normY * 85;
    };

    const handleMouseLeave = () => {
      camera.targetX = 0;
      camera.targetY = 0;
    };

    const handleScroll = () => {
      updateInputRect();
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseleave", handleMouseLeave);
    window.addEventListener("scroll", handleScroll, { passive: true });

    const periodicCheck = setInterval(updateInputRect, 1500);

    // Distance and normal to rounded rectangle (stadium shape)
    // Returns signed distance in pixels from rounded box boundary
    const getStadiumDistanceAndNormal = (px: number, py: number) => {
      const dx = px - inputRect.cx;
      const dy = py - inputRect.cy;

      // Straight horizontal segment extends from -(halfW - radius) to +(halfW - radius)
      const straightHalfW = Math.max(0, inputRect.halfW - inputRect.radius);
      const clampedX = Math.max(-straightHalfW, Math.min(straightHalfW, dx));
      const clampedY = 0;

      // Vector from closest line segment core to point
      const diffX = dx - clampedX;
      const diffY = dy - clampedY;
      const distFromCore = Math.sqrt(diffX * diffX + diffY * diffY);

      // Distance from outer pill edge (positive = outside, negative = inside)
      const distFromEdge = distFromCore - inputRect.radius;

      // Outward normal vector
      let nx = 0;
      let ny = 0;
      if (distFromCore > 0.001) {
        nx = diffX / distFromCore;
        ny = diffY / distFromCore;
      }

      return { distFromEdge, nx, ny, dx, dy };
    };

    // Render loop
    const render = () => {
      // 1. Pure black base
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, width, height);

      // 2. Smooth camera easing
      camera.x += (camera.targetX - camera.x) * 0.05;
      camera.y += (camera.targetY - camera.y) * 0.05;

      const fov = camera.fov;

      // 3. Render Lensed Halo around the rounded rectangular input
      // This produces the soft luminous warped transition visible around the reference input pill
      ctx.save();
      const haloWidth = inputRect.halfW + 45;
      const haloHeight = inputRect.halfH + 35;
      const haloGrad = ctx.createRadialGradient(
        inputRect.cx,
        inputRect.cy,
        inputRect.halfH * 0.5,
        inputRect.cx,
        inputRect.cy,
        haloWidth * 1.15
      );
      haloGrad.addColorStop(0, "rgba(255, 255, 255, 0.055)");
      haloGrad.addColorStop(0.25, "rgba(230, 240, 255, 0.035)");
      haloGrad.addColorStop(0.65, "rgba(180, 205, 255, 0.012)");
      haloGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.fillStyle = haloGrad;
      ctx.beginPath();
      // Draw outer stadium halo
      const hStrW = Math.max(0, haloWidth - haloHeight);
      ctx.arc(inputRect.cx - hStrW, inputRect.cy, haloHeight, Math.PI * 0.5, Math.PI * 1.5);
      ctx.arc(inputRect.cx + hStrW, inputRect.cy, haloHeight, -Math.PI * 0.5, Math.PI * 0.5);
      ctx.closePath();
      ctx.fill();
      ctx.restore();

      // 4. Update and Render 3D Stars with Local Gravitational Warp
      for (let i = 0; i < stars.length; i++) {
        const star = stars[i];

        if (!prefersReducedMotion) {
          // Continuous drift in 3D
          star.x += star.vx;
          star.y += star.vy;
          star.z -= star.vz; // Move forward toward camera

          // Recycle stars when passing camera plane or exceeding bounds
          if (star.z < 60) {
            star.z = 1100;
            star.x = (Math.random() - 0.5) * width * 2.8;
            star.y = (Math.random() - 0.5) * height * 2.8;
            star.history = [];
          }
        }

        // Apply 3D Camera Pan (parallax is strictly proportional to depth: 1/z)
        const camX = star.x - camera.x;
        const camY = star.y - camera.y;

        // 3D Perspective Projection
        const scale = fov / star.z;
        const projX = width / 2 + camX * scale;
        const projY = height / 2 + camY * scale;

        // Gravitational Warp around the central rounded rectangular input
        const { distFromEdge, nx, ny } = getStadiumDistanceAndNormal(projX, projY);

        let finalX = projX;
        let finalY = projY;
        let finalAlpha = star.brightness * Math.min(1.0, (1200 - star.z) / 450);
        let finalSize = star.size * scale * 1.5;

        // Warp Zone: 0 to 180px outside input boundary
        const warpThreshold = 175;

        if (distFromEdge < warpThreshold && distFromEdge > -inputRect.radius * 0.8) {
          // Normalised proximity: 1.0 at edge, 0.0 at threshold
          const proximity = Math.max(0, (warpThreshold - Math.max(0, distFromEdge)) / warpThreshold);

          // Gravitational lensing trajectory bend:
          // Deflects particles tangentially along the pill boundary (stream/flow around edges)
          // Tangent vector: (-ny, nx)
          const tangentX = -ny;
          const tangentY = nx;

          // Strong curved flow along the rounded perimeter
          const bendMag = Math.pow(proximity, 1.4) * 42;
          // Slight radial push to prevent particles from collapsing into the black interior
          const repulseMag = Math.pow(proximity, 2.2) * 16;

          finalX += tangentX * bendMag + nx * repulseMag;
          finalY += tangentY * bendMag + ny * repulseMag;

          // Inside the input itself? The interior is pure black: fade out completely
          if (distFromEdge < 0) {
            finalAlpha *= Math.max(0, 1 + distFromEdge / (inputRect.radius * 0.5));
          } else {
            // Lensed particles brighten noticeably near the gravitational perimeter
            finalAlpha = Math.min(1.0, finalAlpha + proximity * 0.55);
            finalSize = Math.max(0.6, finalSize * (1 + proximity * 0.5));
          }

          // Generate curved streaks near perimeter
          if (!prefersReducedMotion && proximity > 0.15) {
            star.history.push({ x: finalX, y: finalY });
            if (star.history.length > 7) {
              star.history.shift();
            }
          } else {
            if (star.history.length > 0) star.history.shift();
          }
        } else {
          // Far away: normal star point, clear history
          if (star.history.length > 0) star.history.shift();
        }

        // Render curved streak trail if present
        if (star.history.length > 1 && finalAlpha > 0.05) {
          ctx.beginPath();
          ctx.moveTo(star.history[0].x, star.history[0].y);
          for (let h = 1; h < star.history.length; h++) {
            ctx.lineTo(star.history[h].x, star.history[h].y);
          }
          ctx.lineTo(finalX, finalY);
          ctx.strokeStyle = `rgba(240, 245, 255, ${finalAlpha * 0.6})`;
          ctx.lineWidth = Math.max(0.5, finalSize * 0.8);
          ctx.lineCap = "round";
          ctx.stroke();
        }

        // Render star point
        if (finalAlpha > 0.04 && finalX >= -20 && finalX <= width + 20 && finalY >= -20 && finalY <= height + 20) {
          ctx.beginPath();
          ctx.arc(finalX, finalY, Math.max(0.4, finalSize), 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255, 255, 255, ${finalAlpha})`;
          ctx.fill();

          // Glint for foreground brighter stars
          if (star.brightness > 0.8 && star.z < 400 && finalAlpha > 0.5) {
            ctx.beginPath();
            ctx.arc(finalX, finalY, finalSize * 2.4, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${finalAlpha * 0.15})`;
            ctx.fill();
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      clearInterval(periodicCheck);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none z-0 block w-full h-full"
    />
  );
}
