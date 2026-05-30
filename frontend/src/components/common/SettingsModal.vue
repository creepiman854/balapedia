<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
        <div class="modal-panel settings-panel">
          <button class="close-btn" @click="$emit('close')">
            <iconify-icon icon="pixel:window-close-solid" noobserver />
          </button>

          <header class="modal-header">
            <h2 class="modal-title">
              <iconify-icon icon="pixel:cog-solid" noobserver />
              SETTINGS
            </h2>
          </header>

          <div class="modal-body">
            <div class="control">
              <div class="control__head">
                <iconify-icon icon="pixel:retro-pc-solid" noobserver />
                <span class="control__label">CRT Intensity</span>
                <span class="control__value">{{ Math.round(crtIntensity * 100) }}%</span>
              </div>
              <input
                class="slider"
                type="range"
                min="0"
                max="100"
                step="1"
                :value="Math.round(crtIntensity * 100)"
                @input="setCrtIntensity($event.target.value / 100)"
              />
            </div>

            <div class="control">
              <div class="control__head">
                <iconify-icon icon="pixel:grid-solid" noobserver />
                <span class="control__label">Joker grid columns</span>
                <span class="control__value">{{ gridColumns }}</span>
              </div>
              <input
                class="slider"
                type="range"
                :min="minGridCols"
                :max="maxGridCols"
                step="1"
                :value="gridColumns"
                @input="setGridColumns($event.target.value)"
              />
              <div class="control__scale">
                <span>{{ minGridCols }}</span>
                <span>{{ maxGridCols }}</span>
              </div>
            </div>

            <!--
              Toggle "Mostrar bloqueados desvelados" (Fase 2).
              OFF (default) → los Jokers/Vouchers/Decks bloqueados se
                              ven con su asset "locked" oficial.
              ON (modo spoiler) → se ve la imagen real, pero desaturada
                              y con brillo reducido (la carta se sigue
                              identificando como bloqueada).
              No afecta a consumables ni sobres (siempre visibles) ni al
              panel de detalle.
            -->
            <div class="control control--toggle">
              <button
                type="button"
                class="toggle-row"
                :class="{ 'toggle-row--on': showSpoiledLocked }"
                role="switch"
                :aria-checked="showSpoiledLocked"
                @click="setShowSpoiledLocked(!showSpoiledLocked)"
              >
                <span class="toggle-row__icon">
                  <iconify-icon icon="pixel:eye-solid" noobserver />
                </span>
                <span class="toggle-row__text">
                  <span class="toggle-row__label">Reveal locked items</span>
                  <span class="toggle-row__hint"> Reveals the actual image of locked items. </span>
                </span>
                <span class="toggle-switch" aria-hidden="true">
                  <span class="toggle-switch__thumb" />
                </span>
              </button>
            </div>

            <p class="hint">Changes are applied automatically.</p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { onMounted, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import { useSettingsStore } from "@/stores/settings";

const emit = defineEmits(["close"]);

const props = defineProps({
  isOpen: { type: Boolean, required: true },
});

const settings = useSettingsStore();

// Extraemos los topes del store junto al resto de valores
const { crtIntensity, gridColumns, showSpoiledLocked, minGridCols, maxGridCols } =
  storeToRefs(settings);

const { setCrtIntensity, setGridColumns, setShowSpoiledLocked } = settings;

function handleEsc(e) {
  if (e.key === "Escape" && props.isOpen) {
    emit("close");
  }
}

onMounted(() => window.addEventListener("keydown", handleEsc));
onBeforeUnmount(() => window.removeEventListener("keydown", handleEsc));
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 18, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.settings-panel {
  width: 380px;
  max-width: calc(100vw - 32px);
  background: $panel-dark;
  position: relative;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.8);
  @include pixel-clip;
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 16px;
  background: transparent;
  border: none;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  color: $text-3;
  font-family: "m6x11plus", monospace;
  font-size: 20px;
  cursor: pointer;
  transition: color 0.15s;

  @include can-hover {
    &:hover {
      color: #e8443a;
    }
  }
}

.modal-header {
  background: $panel-mid;
  padding: 24px 32px 20px;
  text-align: center;
  border-bottom: 2px solid rgba(255, 255, 255, 0.05);
}

.modal-title {
  font-family: "m6x11plus", monospace;
  font-size: 20px;
  color: #fff;
  margin: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

.modal-body {
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.control {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control__head {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: "m6x11plus", monospace;
  font-size: 15px;
  color: $text-1;
}

.control__head iconify-icon {
  font-size: 18px;
  line-height: 1;
}

.control__label {
  flex: 1;
  font-size: 15px;
  letter-spacing: 0.5px;
}

.control__value {
  font-family: "m6x11plus", monospace;
  color: $text-2;
  min-width: 60px;
  text-align: right;
  font-size: 14px;
}

.control__scale {
  display: flex;
  justify-content: space-between;
  font-family: "m6x11plus", monospace;
  font-size: 10px;
  color: $text-3;
}

.slider {
  appearance: none;
  width: 100%;
  height: 6px;
  background: $panel-darkest;
  cursor: pointer;
  @include pixel-clip-sm;
}

.slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  background: $text-1;
  border: 2px solid $panel-medlight;
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: $text-1;
  border: 2px solid $panel-medlight;
}

iconify-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.hint {
  font-family: "m6x11plus", monospace;
  font-size: 11px;
  color: $text-3;
  text-align: center;
  margin-top: 4px;
}

/*
 * Toggle row: imita el look de un switch sobre un control. El click en
 * cualquier parte de la fila (icono / label / hint / switch) cambia el
 * valor — feedback visual del switch a la derecha. role="switch" para
 * accesibilidad.
 */
.control--toggle {
  gap: 0;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
  transition: filter 0.15s;

  @include can-hover {
    &:hover {
      filter: brightness(1.15);
    }
  }
  &:active {
    transform: scale(0.99);
  }
}

.toggle-row__icon {
  font-size: 18px;
  line-height: 1;
  color: $text-1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.toggle-row__text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.toggle-row__label {
  font-family: "m6x11plus", monospace;
  font-size: 15px;
  color: $text-1;
  letter-spacing: 0.5px;
}

.toggle-row__hint {
  font-family: "m6x11plus", monospace;
  font-size: 10px;
  color: $text-3;
  letter-spacing: 0.3px;
  line-height: 1.3;
}

.toggle-switch {
  flex-shrink: 0;
  width: 36px;
  height: 18px;
  background: $panel-darkest;
  position: relative;
  transition: background 0.18s ease;
}

.toggle-switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: $panel-light;
  transition:
    left 0.18s ease,
    background 0.18s ease;
}

.toggle-row--on .toggle-switch {
  background: #22c55e;
}

.toggle-row--on .toggle-switch__thumb {
  left: 20px;
  background: #ffffff;
}

/* Transición del modal (misma que AuthModal) */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

/* ──────────────────────────────────────────────────────────────
 * TABLET — el modal crece ligeramente para aprovechar el ancho.
 * ────────────────────────────────────────────────────────────── */
@include tablet-only {
  .settings-panel {
    width: 460px;
  }

  .modal-title {
    font-size: 24px;
  }

  .control__head {
    font-size: 17px;
  }

  .control__label {
    font-size: 17px;
  }

  .control__value {
    font-size: 16px;
    min-width: 72px;
  }

  .slider {
    height: 8px;
  }

  .slider::-webkit-slider-thumb {
    width: 20px;
    height: 20px;
  }

  .slider::-moz-range-thumb {
    width: 20px;
    height: 20px;
  }

  .toggle-row__icon {
    font-size: 22px;
  }

  .toggle-row__label {
    font-size: 17px;
  }

  .toggle-row__hint {
    font-size: 11px;
  }

  .toggle-switch {
    width: 44px;
    height: 22px;
  }

  .toggle-switch__thumb {
    width: 18px;
    height: 18px;
  }

  .toggle-row--on .toggle-switch__thumb {
    left: 24px;
  }

  .hint {
    font-size: 12px;
  }
}

/* ──────────────────────────────────────────────────────────────
 * MOBILE — full-screen sheet. Quitamos pixel-clip (no aplica en
 * pantalla completa), eliminamos los márgenes y dejamos que el body
 * haga scroll vertical interno si los controles superan el alto.
 * ────────────────────────────────────────────────────────────── */
@include mobile {
  .modal-backdrop {
    align-items: stretch;
    justify-content: stretch;
    backdrop-filter: none;
    background: $panel-dark;
  }

  .settings-panel {
    width: 100vw;
    max-width: 100vw;
    height: 100vh;
    max-height: 100vh;
    clip-path: none;
    box-shadow: none;
    display: flex;
    flex-direction: column;
  }

  .close-btn {
    top: 10px;
    right: 12px;
    font-size: 28px;
  }

  .modal-header {
    padding: 22px 24px 18px;
  }

  .modal-title {
    font-size: 22px;
    gap: 12px;
  }

  .modal-body {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 24px;
    gap: 22px;
  }

  .control {
    gap: 10px;
  }

  .control__head {
    font-size: 17px;
    gap: 12px;
  }

  .control__head iconify-icon {
    font-size: 22px;
  }

  .control__label {
    font-size: 17px;
  }

  .control__value {
    font-size: 16px;
    min-width: 72px;
  }

  .control__scale {
    font-size: 12px;
  }

  .slider {
    height: 10px;
  }

  .slider::-webkit-slider-thumb {
    width: 24px;
    height: 24px;
  }

  .slider::-moz-range-thumb {
    width: 24px;
    height: 24px;
  }

  .toggle-row {
    padding: 14px 4px;
    gap: 14px;
  }

  .toggle-row__icon {
    font-size: 24px;
  }

  .toggle-row__label {
    font-size: 17px;
  }

  .toggle-row__hint {
    font-size: 12px;
    line-height: 1.4;
  }

  .toggle-switch {
    width: 52px;
    height: 26px;
  }

  .toggle-switch__thumb {
    width: 22px;
    height: 22px;
  }

  .toggle-row--on .toggle-switch__thumb {
    left: 28px;
  }

  .hint {
    font-size: 13px;
    margin-top: 8px;
  }
}
</style>
