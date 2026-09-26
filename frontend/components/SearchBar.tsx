"use client";

import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { Search, CornerDownLeft, Sparkles, X, Plus } from "lucide-react";

interface SearchBarProps {
  initialQuery?: string;
  autoFocus?: boolean;
  onSearch?: (query: string) => void;
  isLoading?: boolean;
}

interface EdgeDotParticle {
  progress: number; // 0 to 1 along perimeter
  distance: number; // offset distance outward from border in px (1 to 32px)
  speed: number;    // orbital speed along stadium perimeter
  radius: number;   // dot size
  alpha: number;
  life: number;
  maxLife: number;
  zDepth: number;   // 3D depth layer (0 = deeper/back, 1 = closer/front)
  wobblePhase: number;
}

export default function SearchBar({
  initialQuery = "",
  autoFocus = false,
  onSearch,
  isLoading = false,
}: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);
  const [isFocused, setIsFocused] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mousePosRef = useRef({ x: 0, y: 0, active: false, speed: 0, lastX: 0, lastY: 0, smoothedSpeed: 0 });
  const router = useRouter();

  // High fidelity canvas effect: Continuous 3D glowing dots around search bar with gravitational parallax
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    let animId: number;
    let width = 0;
    let height = 0;
    const pad = 96; // Wide padding around search box

    const updateCanvasSize = () => {
      const rect = container.getBoundingClientRect();
      width = canvas.width = Math.round(rect.width + pad * 2);
      height = canvas.height = Math.round(rect.height + pad * 2);
    };

    updateCanvasSize();

    // Plentiful glowing dots along the border
    const dotCount = 85;
    const dots: EdgeDotParticle[] = [];

    const createDot = (randomProgress = true): EdgeDotParticle => ({
      progress: randomProgress ? Math.random() : 0,
      // Grouped closely around the stadium border
      distance: 1.0 + Math.pow(Math.random(), 1.8) * 30,
      // Calm, slow baseline orbital speed
      speed: (0.00015 + Math.random() * 0.00035) * (Math.random() < 0.2 ? -1 : 1),
      radius: 0.8 + Math.random() * 1.6,
      alpha: 0.25 + Math.random() * 0.65,
      life: 0,
      maxLife: 280 + Math.random() * 320,
      zDepth: Math.random(), // 3D depth layer (0 = back, 1 = front)
      wobblePhase: Math.random() * Math.PI * 2,
    });

    for (let i = 0; i < dotCount; i++) {
      dots.push(createDot(true));
    }

    // Helper: compute coordinates and tangent vector on the stadium perimeter + outward offset
    const getStadiumPoint = (
      progress: number,
      outwardOffset: number,
      boxW: number,
      boxH: number,
      radius: number,
      zDepth: number,
      mouseParallaxX: number,
      mouseParallaxY: number
    ) => {
      // Stadium geometry: 2 horizontal straight segments and 2 semicircles
      const straightLength = Math.max(0, boxW - 2 * radius);
      const curveLength = Math.PI * radius;
      const totalPerimeter = 2 * straightLength + 2 * curveLength;

      // Wrap progress
      let p = (progress % 1 + 1) % 1;
      let dist = p * totalPerimeter;

      const cx = width / 2;
      const cy = height / 2;

      let x = 0;
      let y = 0;

      // 3D perspective tilt: back dots sit slightly compressed vertically
      const depthScaleY = 0.90 + zDepth * 0.20;

      if (dist < straightLength) {
        // Top edge: moving left to right
        const t = dist / straightLength;
        const coreX = -straightLength / 2 + t * straightLength;
        const coreY = -boxH / 2;
        x = cx + coreX;
        y = cy + (coreY - outwardOffset) * depthScaleY;
      } else if (dist < straightLength + curveLength) {
        // Right semicircle: angle from -PI/2 to PI/2
        const arcDist = dist - straightLength;
        const angle = -Math.PI / 2 + (arcDist / curveLength) * Math.PI;
        const centerArcX = straightLength / 2;
        const r = radius + outwardOffset;
        x = cx + centerArcX + Math.cos(angle) * r;
        y = cy + Math.sin(angle) * r * depthScaleY;
      } else if (dist < 2 * straightLength + curveLength) {
        // Bottom edge: moving right to left
        const botDist = dist - (straightLength + curveLength);
        const t = botDist / straightLength;
        const coreX = straightLength / 2 - t * straightLength;
        const coreY = boxH / 2;
        x = cx + coreX;
        y = cy + (coreY + outwardOffset) * depthScaleY;
      } else {
        // Left semicircle: angle from PI/2 to 3*PI/2
        const arcDist = dist - (2 * straightLength + curveLength);
        const angle = Math.PI / 2 + (arcDist / curveLength) * Math.PI;
        const centerArcX = -straightLength / 2;
        const r = radius + outwardOffset;
        x = cx + centerArcX + Math.cos(angle) * r;
        y = cy + Math.sin(angle) * r * depthScaleY;
      }

      // Apply 3D mouse parallax displacement:
      // Front dots (zDepth close to 1) shift more with the mouse; back dots shift less or opposite
      const depthParallaxMultiplier = (zDepth - 0.45) * 16;
      x += mouseParallaxX * depthParallaxMultiplier;
      y += mouseParallaxY * depthParallaxMultiplier;

      return { x, y };
    };

    let animationTime = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);
      animationTime += 0.012;

      const rect = container.getBoundingClientRect();
      const boxW = rect.width;
      const boxH = rect.height;
      if (boxW <= 0 || boxH <= 0) {
        animId = requestAnimationFrame(render);
        return;
      }
      const radius = Math.max(0, boxH / 2);
      const cx = width / 2;
      const cy = height / 2;

      // Mouse speed tracking & smooth damping
      const m = mousePosRef.current;
      m.smoothedSpeed += (m.speed - m.smoothedSpeed) * 0.08;
      m.speed *= 0.90; // Natural decay

      // Smooth, controlled acceleration: calm baseline (1.0), gentle boost up to 2.2x on cursor move
      const speedMultiplier = 1.0 + Math.min(1.2, m.smoothedSpeed * 0.08) + (isHovered ? 0.2 : 0);

      // Normalized mouse offset relative to center of search bar [-1, 1]
      const mouseDx = m.active ? (m.x - (rect.left + boxW / 2)) / (window.innerWidth / 2) : 0;
      const mouseDy = m.active ? (m.y - (rect.top + boxH / 2)) / (window.innerHeight / 2) : 0;

      // 1. Subtle 3D Black Hole Gravitational Halo around perimeter
      const haloStrength = isFocused ? 1.3 : isHovered ? 1.15 : 1.0;

      ctx.save();
      const haloLayers = [
        { blur: 24, alpha: 0.05 * haloStrength, spread: 22, width: 2.0 },
        { blur: 14, alpha: 0.09 * haloStrength, spread: 11, width: 1.6 },
        { blur: 6,  alpha: 0.16 * haloStrength, spread: 3,  width: 1.2 },
        { blur: 2,  alpha: 0.26 * haloStrength, spread: 1,  width: 1.0 },
      ];

      for (const layer of haloLayers) {
        ctx.beginPath();
        const curRadius = radius + layer.spread;
        const curStrHalfW = Math.max(0, (boxW + layer.spread * 2) / 2 - curRadius);
        // 3D parallax shift responsive to mouse
        const shiftX = mouseDx * (layer.spread * 0.18);
        const shiftY = mouseDy * (layer.spread * 0.18);

        ctx.arc(cx - curStrHalfW + shiftX, cy + shiftY, curRadius, Math.PI * 0.5, Math.PI * 1.5);
        ctx.arc(cx + curStrHalfW + shiftX, cy + shiftY, curRadius, -Math.PI * 0.5, Math.PI * 0.5);
        ctx.closePath();

        ctx.shadowColor = `rgba(240, 245, 255, ${layer.alpha})`;
        ctx.shadowBlur = layer.blur;
        ctx.strokeStyle = `rgba(245, 248, 255, ${layer.alpha * 0.75})`;
        ctx.lineWidth = layer.width;
        ctx.stroke();
      }
      ctx.restore();

      // 2. Render Continuous 3D Glowing Dots around perimeter
      // Sorted by zDepth so foreground dots naturally render on top
      dots.sort((a, b) => a.zDepth - b.zDepth);

      for (let i = 0; i < dots.length; i++) {
        const d = dots[i];
        // Steady continuous movement, responsive to cursor speed
        d.progress += d.speed * speedMultiplier;
        d.life++;

        if (d.life > d.maxLife) {
          dots[i] = createDot(false);
          continue;
        }

        // Gentle 3D gravitational orbital wobble
        const subtleWobble = Math.sin(animationTime * 1.5 + d.wobblePhase) * (1.8 * d.zDepth + 0.5);
        const currentDist = d.distance + subtleWobble;

        // Position on perimeter in 3D with mouse parallax
        const pt = getStadiumPoint(
          d.progress,
          currentDist,
          boxW,
          boxH,
          radius,
          d.zDepth,
          mouseDx,
          mouseDy
        );

        // Life fade factor (smooth fade in and out)
        const lifeFactor = Math.sin((d.life / d.maxLife) * Math.PI);
        // Foreground dots are brighter and slightly larger
        const depthBrightness = 0.55 + d.zDepth * 0.65;
        const dotAlpha = d.alpha * lifeFactor * depthBrightness * (isHovered ? 1.2 : 1.0);

        if (dotAlpha < 0.02) continue;

        const dotSize = d.radius * (0.8 + d.zDepth * 0.5);

        // Outer soft glow for dot
        const outerDotR = Math.max(0, dotSize * 2.2);
        if (outerDotR > 0) {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, outerDotR, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255, 255, 255, ${dotAlpha * 0.22})`;
          ctx.fill();
        }

        // Intense glowing dot core
        const coreDotR = Math.max(0, dotSize);
        if (coreDotR > 0) {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, coreDotR, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(245, 248, 255, ${dotAlpha})`;
          ctx.fill();
        }

        // Extra twinkle highlight for closest foreground dots
        if (d.zDepth > 0.7 && dotAlpha > 0.4) {
          const twinkleDotR = Math.max(0, dotSize * 0.5);
          if (twinkleDotR > 0) {
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, twinkleDotR, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${Math.min(1.0, dotAlpha * 1.5)})`;
            ctx.fill();
          }
        }
      }

      // 3. Clear and punch pure black mask inside the search box boundary
      ctx.save();
      ctx.globalCompositeOperation = "destination-out";
      ctx.beginPath();
      const innerRadius = Math.max(0, radius - 0.5);
      const innerStrHalfW = Math.max(0, boxW / 2 - radius);
      ctx.arc(cx - innerStrHalfW, cy, innerRadius, Math.PI * 0.5, Math.PI * 1.5);
      ctx.arc(cx + innerStrHalfW, cy, innerRadius, -Math.PI * 0.5, Math.PI * 0.5);
      ctx.closePath();
      ctx.fillStyle = "#000000";
      ctx.fill();
      ctx.restore();

      animId = requestAnimationFrame(render);
    };

    render();

    const handleResize = () => {
      updateCanvasSize();
    };

    // Track mouse speed and viewport position for dynamic acceleration and 3D parallax
    const handleWindowMouseMove = (e: MouseEvent) => {
      const m = mousePosRef.current;
      m.x = e.clientX;
      m.y = e.clientY;
      m.active = true;

      if (m.lastX !== 0 || m.lastY !== 0) {
        const dx = e.clientX - m.lastX;
        const dy = e.clientY - m.lastY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        m.speed = Math.max(m.speed, Math.min(dist, 25));
      }
      m.lastX = e.clientX;
      m.lastY = e.clientY;
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleWindowMouseMove);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleWindowMouseMove);
    };
  }, [isFocused, isHovered]);

  const handleSubmit = (e?: FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    if (onSearch) {
      onSearch(trimmed);
    } else {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    mousePosRef.current = {
      ...mousePosRef.current,
      x: e.clientX,
      y: e.clientY,
      active: true,
    };
  };

  const handleMouseLeave = () => {
    mousePosRef.current.active = false;
    setIsHovered(false);
  };

  const demoSuggestions = [
    "Find the architecture PDF Rahul sent me around February. It had PostgreSQL and BLE.",
    "Find the screenshot with the PostgreSQL architecture.",
    "Find the product launch presentation for commercial sensors.",
    "Find the security audit document about cloud infrastructure.",
  ];

  return (
    <div className="w-full flex flex-col items-center gap-3">
      {/* Search Input Box Wrapper */}
      <div
        ref={containerRef}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={handleMouseLeave}
        className="w-full relative flex items-center justify-center"
      >
        {/* Spatial Distortion Canvas (3D Black Hole Accretion Disk & Perimeter Lensing) */}
        <canvas
          ref={canvasRef}
          aria-hidden="true"
          className="absolute -top-24 -bottom-24 -left-24 -right-24 w-[calc(100%+192px)] h-[calc(100%+192px)] pointer-events-none z-0"
        />

        {/* The Search Bar: Wide, compact height, pitch black glass, low contrast border */}
        <form
          data-grav-input="true"
          onSubmit={handleSubmit}
          className={`w-full relative z-10 flex items-center rounded-full bg-black/95 transition-all duration-300 px-4 py-2 sm:py-2.5 border ${
            isFocused
              ? "border-white/[0.22] shadow-[0_12px_45px_rgba(0,0,0,0.98),0_0_1px_1px_rgba(255,255,255,0.18)]"
              : isHovered
              ? "border-white/[0.16] shadow-[0_10px_35px_rgba(0,0,0,0.95)]"
              : "border-white/[0.10] shadow-[0_8px_30px_rgba(0,0,0,0.90)]"
          }`}
        >
          {/* Extremely subtle interior bevel for glass depth */}
          <div className="absolute inset-0 rounded-full pointer-events-none shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),inset_0_-1px_1px_rgba(0,0,0,0.9)]" />

          {/* Left search icon */}
          <div className="pl-2 pr-3 text-zinc-400 flex items-center justify-center">
            <Search className="w-5 h-5 text-zinc-400" />
          </div>

          {/* Search text input */}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            autoFocus={autoFocus}
            placeholder="What do you remember? (e.g. Rahul's architecture PDF around February with BLE...)"
            className="w-full py-3 sm:py-3.5 text-base sm:text-lg text-zinc-100 placeholder:text-zinc-400/80 bg-transparent focus:outline-none font-normal"
          />

          {/* Clear button */}
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="p-2 mr-1 text-zinc-400 hover:text-white rounded-full hover:bg-white/[0.08] transition-colors"
              title="Clear"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          {/* Action buttons sitting cleanly inside */}
          <div className="pr-1 flex items-center gap-2">
            <button
              type="submit"
              disabled={!query.trim() || isLoading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-white/[0.08] hover:bg-white/[0.16] disabled:opacity-40 disabled:hover:bg-white/[0.08] text-white text-sm font-medium border border-white/[0.12] hover:border-white/[0.24] transition-all shadow-[0_0_15px_-3px_rgba(255,255,255,0.06)]"
            >
              {isLoading ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Search</span>
                  <CornerDownLeft className="w-4 h-4 opacity-75" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Quick-try memory suggestions */}
      <div className="w-full flex flex-wrap items-center justify-start gap-2 pt-1.5">
        <span className="text-xs sm:text-sm text-zinc-400 flex items-center gap-1.5 mr-1 font-mono font-medium">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          Try memory:
        </span>
        {demoSuggestions.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => {
              setQuery(prompt);
              if (onSearch) {
                onSearch(prompt);
              } else {
                router.push(`/search?q=${encodeURIComponent(prompt)}`);
              }
            }}
            className="text-xs sm:text-sm px-3.5 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.08] hover:border-white/[0.18] text-zinc-300 hover:text-white transition-all text-left max-w-full truncate backdrop-blur-sm"
          >
            {prompt.length > 55 ? prompt.slice(0, 52) + "..." : prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
