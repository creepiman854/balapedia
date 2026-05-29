<template>
  <div class="loader-overlay">
    <div class="loader-content" :class="{ 'is-floating': isLoading }">
      <canvas ref="canvasRef" width="142" height="190"></canvas>
      <p class="loader-text" :style="{ opacity: isLoading ? 1 : 0 }">Loading cards...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from "vue";

const props = defineProps({
  isLoading: { type: Boolean, default: true },
});

const emit = defineEmits(["hidden"]);
const canvasRef = ref(null);

let gl = null;
let program = null;
let dissolveLoc = null;
let texture = null;
let animationId = null;
let dissolveValue = 0;

// Vertex Shader (Mapea coordenadas y texturas)
const vsSource = `
  attribute vec2 a_position;
  varying vec2 v_uv;
  void main() {
    v_uv = a_position * 0.5 + 0.5;
    v_uv.y = 1.0 - v_uv.y; // Invertir Y en WebGL
    gl_Position = vec4(a_position, 0.0, 1.0);
  }
`;

// Fragment Shader (Adaptación del shader de Godot a GLSL con ruido procedural FBM)
const fsSource = `
  precision highp float;
  varying vec2 v_uv;
  uniform sampler2D u_main_texture;
  uniform float u_dissolve;

  const float u_burn_size = 0.06;
  const vec4 u_burn_color = vec4(1.0, 0.35, 0.05, 1.0); // Naranja fuego

  // Ruido Procedural (Simplex 2D)
  vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
  float snoise(vec2 v){
    const vec4 C = vec4(0.211324865, 0.366025403, -0.577350269, 0.024390243);
    vec2 i  = floor(v + dot(v, C.yy) );
    vec2 x0 = v -   i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod(i, 289.0);
    vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 )) + i.x + vec3(0.0, i1.x, 1.0 ));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m; m = m*m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.7928429 - 0.8537347 * ( a0*a0 + h*h );
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
  }

  // Ruido Fractal (FBM) para imitar textura de quemado
  float fbm(vec2 p) {
      float f = 0.0; float w = 0.5;
      for (int i = 0; i < 4; i++) {
          f += w * snoise(p); p *= 2.0; w *= 0.5;
      }
      return f * 0.5 + 0.5;
  }

  void main() {
    vec4 tex_color = texture2D(u_main_texture, v_uv);

    // Ignorar píxeles transparentes de la carta original para no quemar el aire
    if (tex_color.a < 0.05) discard;

    float noise_val = fbm(v_uv * 1.0);

    // Convertir dissolve (0 a 1) al rango del ruido sumando el tamaño del quemado
    float burn_edge = u_dissolve * (1.0 + u_burn_size);

    // step(edge, x) -> 0.0 si x < edge, 1.0 si x > edge
    float alpha = step(burn_edge, noise_val);
    float is_border = step(burn_edge, noise_val) - step(burn_edge + u_burn_size, noise_val);

    vec3 final_rgb = mix(tex_color.rgb, u_burn_color.rgb, is_border);
    gl_FragColor = vec4(final_rgb, tex_color.a * alpha);
  }
`;

function createShader(type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error(gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

function initWebGL() {
  const canvas = canvasRef.value;
  gl = canvas.getContext("webgl", { alpha: true, premultipliedAlpha: false });

  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  const vertShader = createShader(gl.VERTEX_SHADER, vsSource);
  const fragShader = createShader(gl.FRAGMENT_SHADER, fsSource);

  program = gl.createProgram();
  gl.attachShader(program, vertShader);
  gl.attachShader(program, fragShader);
  gl.linkProgram(program);
  gl.useProgram(program);

  const vertices = new Float32Array([-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0]);
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

  const posLoc = gl.getAttribLocation(program, "a_position");
  gl.enableVertexAttribArray(posLoc);
  gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

  dissolveLoc = gl.getUniformLocation(program, "u_dissolve");

  // Elegir un palo aleatorio
  const suits = ["Spades", "Hearts", "Clubs", "Diamonds"];
  const randomSuit = suits[Math.floor(Math.random() * suits.length)];

  // Cargar imagen local (¡Asegúrate de tenerla en esta ruta!)
  const img = new Image();
  img.src = `/images/Ace_of_${randomSuit}.png`;
  img.onload = () => {
    texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    render();
  };
}

function render() {
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);
  gl.uniform1f(dissolveLoc, dissolveValue);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
}

function startDissolve() {
  const duration = 650; // ms que dura la desintegración
  const startTime = performance.now();

  function animate(time) {
    const elapsed = time - startTime;
    dissolveValue = Math.min(elapsed / duration, 1.0);
    render();

    if (dissolveValue < 1.0) {
      animationId = requestAnimationFrame(animate);
    } else {
      emit("hidden"); // Avisa al padre de que la carta se ha desintegrado por completo
    }
  }
  animationId = requestAnimationFrame(animate);
}

watch(
  () => props.isLoading,
  (newVal) => {
    if (newVal) {
      cancelAnimationFrame(animationId);
      dissolveValue = 0;
      render();
    } else {
      startDissolve();
    }
  },
);

onMounted(() => {
  initWebGL();
});

onBeforeUnmount(() => {
  if (animationId) cancelAnimationFrame(animationId);
  if (gl && texture) gl.deleteTexture(texture);
  if (gl && program) gl.deleteProgram(program);
});
</script>

<style lang="scss" scoped>
.loader-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  pointer-events: none;
}

.loader-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.6));
}

.is-floating canvas {
  animation: floatCard 2.5s ease-in-out infinite;
}

@keyframes floatCard {
  0%,
  100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-12px) rotate(2deg);
  }
}

.loader-text {
  font-family: "m6x11plus", monospace;
  font-size: 22px;
  color: #cfd6d8;
  letter-spacing: 1px;
  margin: 0;
  text-shadow: 0 3px 6px rgba(0, 0, 0, 0.8);
  transition: opacity 0.2s ease;
}
</style>
