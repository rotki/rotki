<script setup lang="ts">
interface ConfettiParticle {
  color: string;
  rotation: number;
  rotationSpeed: number;
  size: number;
  velocityX: number;
  velocityY: number;
  x: number;
  y: number;
}

// Composable: Use this to manage confetti animation
function useConfetti() {
  // Refs
  const confettiCanvas = ref<HTMLCanvasElement | null>(null);
  const ctx = ref<CanvasRenderingContext2D | null>(null);
  const confettiParticles = ref<ConfettiParticle[]>([]);
  let animationFrameId: number;

  const PARTICLE_COUNT = 150;
  const COLORS = ['#FFC107', '#4CAF50', '#2196F3', '#FF5722', '#9C27B0'];

  // Initialize Canvas
  function initializeCanvas(): void {
    const canvas = get(confettiCanvas);
    if (!canvas) {
      return;
    }
    set(ctx, canvas.getContext('2d'));
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  // Create particles
  function createParticles(): void {
    const canvas = get(confettiCanvas);
    if (!canvas) {
      return;
    }

    set(confettiParticles, []);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      get(confettiParticles).push({
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        rotation: Math.random() * 360,
        rotationSpeed: Math.random() * 4 - 2,
        size: Math.random() * 8 + 2,
        velocityX: Math.random() * 4 - 2,
        velocityY: Math.random() * 4 + 2,
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height - canvas.height,
      });
    }
  }

  // Render animation
  function renderParticles(): void {
    const ctxInstance = get(ctx);
    const canvas = get(confettiCanvas);

    if (!ctxInstance || !canvas) {
      return;
    }

    // Clear the canvas
    ctxInstance.clearRect(0, 0, canvas.width, canvas.height);

    // Draw each particle
    set(confettiParticles, get(confettiParticles).filter((particle) => {
      ctxInstance.save();

      // Apply color and transformation
      ctxInstance.fillStyle = particle.color;
      ctxInstance.translate(particle.x, particle.y);
      ctxInstance.rotate((particle.rotation * Math.PI) / 180);

      // Draw confetti (rectangle)
      ctxInstance.fillRect(
        -particle.size / 2,
        -particle.size / 2,
        particle.size,
        particle.size,
      );

      ctxInstance.restore();

      // Update particle position and rotation
      particle.x += particle.velocityX;
      particle.y += particle.velocityY;
      particle.rotation += particle.rotationSpeed;

      // Keep particle if it's still within bounds
      return particle.y <= canvas.height;
    }));

    // Continue the animation if particles remain
    if (get(confettiParticles).length > 0) {
      animationFrameId = requestAnimationFrame(renderParticles);
    }
    else {
      cancelAnimationFrame(animationFrameId);
    }
  }

  // Start Confetti Animation
  function startConfetti(): void {
    createParticles();
    renderParticles();
  }

  // Canvas resizing
  function resizeCanvas(): void {
    initializeCanvas();
  }

  // Cleanup
  function stopConfetti(): void {
    cancelAnimationFrame(animationFrameId);
  }

  return {
    confettiCanvas,
    initializeCanvas,
    resizeCanvas,
    startConfetti,
    stopConfetti,
  };
}

const {
  confettiCanvas,
  initializeCanvas,
  resizeCanvas,
  startConfetti,
  stopConfetti,
} = useConfetti();

// Lifecycle hooks
onMounted(() => {
  initializeCanvas();
  window.addEventListener('resize', resizeCanvas);

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        startConfetti();
        observer.disconnect();
      }
    });
  });

  const canvas = get(confettiCanvas);
  if (canvas) {
    observer.observe(canvas);
  }
});

onBeforeUnmount(() => {
  stopConfetti();
  window.removeEventListener('resize', resizeCanvas);
});
</script>

<template>
  <canvas
    ref="confettiCanvas"
    class="absolute inset-0 pointer-events-none"
  />
</template>
