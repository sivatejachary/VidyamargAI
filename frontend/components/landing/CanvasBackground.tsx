"use client";

import React, { useEffect, useRef } from "react";

export default function CanvasBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Mouse coordinates (current and target for smooth lerped lag)
    const mouse = { x: width / 2, y: height / 2, targetX: width / 2, targetY: height / 2 };

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouse.targetX = e.clientX;
      mouse.targetY = e.clientY;
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);

    // Initialize particles (Layer 3)
    const particleCount = 40;
    const particles: Array<{
      x: number;
      y: number;
      size: number;
      speedY: number;
      speedX: number;
      alpha: number;
    }> = [];

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 1.5 + 0.6,
        speedY: -(Math.random() * 0.35 + 0.15),
        speedX: (Math.random() - 0.5) * 0.15,
        alpha: Math.random() * 0.4 + 0.1,
      });
    }

    // Coordinates for mesh gradient glow nodes
    const glowCircles = [
      { x: width * 0.2, y: height * 0.3, radius: 350, vx: 0.2, vy: 0.15 },
      { x: width * 0.8, y: height * 0.7, radius: 400, vx: -0.15, vy: 0.25 },
      { x: width * 0.5, y: height * 0.4, radius: 380, vx: 0.1, vy: -0.2 }
    ];

    let time = 0;

    const render = () => {
      time += 0.002;

      // Detect active theme
      const isDark = !document.documentElement.classList.contains("light-theme");

      // Mouse position lerping
      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;

      ctx.clearRect(0, 0, width, height);

      // --- Base Background Color ---
      ctx.fillStyle = isDark ? "#09090b" : "#f4f4f5"; // Dark Zinc vs Light Zinc
      ctx.fillRect(0, 0, width, height);

      // --- Layer 1 & 4: Mesh Gradient & Moving Glow Circles ---
      glowCircles.forEach((circle, idx) => {
        const currentX = circle.x + Math.sin(time * 0.8 + idx * 3) * 120;
        const currentY = circle.y + Math.cos(time * 1.2 + idx * 7) * 100;

        const circleColor = isDark
          ? [
              "rgba(99, 102, 241, 0.05)",  // Indigo
              "rgba(139, 92, 246, 0.04)",  // Violet
              "rgba(148, 163, 184, 0.02)"  // Slate
            ][idx]
          : [
              "rgba(99, 102, 241, 0.03)",  // Indigo
              "rgba(139, 92, 246, 0.025)", // Violet
              "rgba(148, 163, 184, 0.015)" // Slate
            ][idx];

        const grad = ctx.createRadialGradient(currentX, currentY, 0, currentX, currentY, circle.radius);
        grad.addColorStop(0, circleColor);
        grad.addColorStop(1, isDark ? "rgba(9, 9, 11, 0)" : "rgba(244, 244, 245, 0)");
        
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(currentX, currentY, circle.radius, 0, Math.PI * 2);
        ctx.fill();
      });

      // --- Layer 2: Aurora Waves ---
      ctx.save();
      ctx.strokeStyle = isDark ? "rgba(147, 51, 234, 0.02)" : "rgba(147, 51, 234, 0.04)";
      ctx.lineWidth = 3.5;
      
      for (let w = 0; w < 3; w++) {
        ctx.beginPath();
        const offset = w * 250;
        const waveHeight = 50 + w * 25;
        
        ctx.moveTo(0, height * 0.45 + Math.sin(time + w) * 60);
        
        for (let x = 0; x <= width; x += 50) {
          const y = height * 0.45 + Math.sin(x * 0.0015 + time + w) * waveHeight + Math.cos(x * 0.001 - time * 0.8) * 40 + offset - 100;
          ctx.lineTo(x, y);
        }
        
        ctx.stroke();
      }
      ctx.restore();

      // --- Layer 5: Digital Grid ---
      ctx.save();
      ctx.strokeStyle = isDark ? "rgba(255, 255, 255, 0.012)" : "rgba(9, 9, 11, 0.035)";
      ctx.lineWidth = 1;

      const gridSpacing = 80;
      // Apply mouse parallax shift
      const shiftX = (mouse.x - width / 2) * -0.02;
      const shiftY = (mouse.y - height / 2) * -0.02;

      // Draw vertical lines
      for (let x = (shiftX % gridSpacing) - gridSpacing; x < width + gridSpacing; x += gridSpacing) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }

      // Draw horizontal lines
      for (let y = (shiftY % gridSpacing) - gridSpacing; y < height + gridSpacing; y += gridSpacing) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
      ctx.restore();

      // --- Layer 3: Floating Particles ---
      ctx.fillStyle = isDark ? "rgba(255, 255, 255, 0.35)" : "rgba(9, 9, 11, 0.15)";
      particles.forEach((p) => {
        // Move particle
        p.y += p.speedY;
        p.x += p.speedX;

        // Wrap around boundary
        if (p.y < 0) {
          p.y = height;
          p.x = Math.random() * width;
        }
        if (p.x < 0 || p.x > width) {
          p.speedX *= -1;
        }

        // Hover distance tracking (glowing up around mouse pointer)
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        let pullX = 0;
        let pullY = 0;
        
        if (dist < 200) {
          const force = (200 - dist) / 200;
          pullX = (dx / dist) * force * 0.3;
          pullY = (dy / dist) * force * 0.3;
        }

        ctx.save();
        ctx.globalAlpha = p.alpha * (0.2 + (dist < 250 ? (250 - dist) / 250 * 0.8 : 0));
        ctx.beginPath();
        ctx.arc(p.x + pullX, p.y + pullY, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });

      // --- Layer 6: Cursor Spotlight Glow ---
      const spotGrad = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 250);
      if (isDark) {
        spotGrad.addColorStop(0, "rgba(168, 85, 247, 0.06)");
        spotGrad.addColorStop(0.4, "rgba(59, 130, 246, 0.03)");
        spotGrad.addColorStop(1, "rgba(9, 9, 11, 0)");
      } else {
        spotGrad.addColorStop(0, "rgba(168, 85, 247, 0.03)");
        spotGrad.addColorStop(0.4, "rgba(59, 130, 246, 0.015)");
        spotGrad.addColorStop(1, "rgba(244, 244, 245, 0)");
      }

      ctx.fillStyle = spotGrad;
      ctx.beginPath();
      ctx.arc(mouse.x, mouse.y, 250, 0, Math.PI * 2);
      ctx.fill();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none z-0"
      style={{ willChange: "transform" }}
    />
  );
}
