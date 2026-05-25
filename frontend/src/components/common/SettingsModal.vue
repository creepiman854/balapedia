<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
        <div class="modal-panel settings-panel">
          <button class="close-btn" @click="$emit('close')">✕</button>

          <header class="modal-header">
            <h2 class="modal-title">
              <iconify-icon icon="pixel:cog-solid" noobserver />
              AJUSTES
            </h2>
          </header>

          <div class="modal-body">
            <div class="control">
              <div class="control__head">
                <iconify-icon icon="pixel:retro-pc-solid" noobserver />
                <span class="control__label">Intensidad CRT</span>
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
                <span class="control__label">Columnas del grid</span>
                <span class="control__value">{{ gridColumns }}</span>
              </div>
              <input
                class="slider"
                type="range"
                :min="COLUMNS_MIN"
                :max="COLUMNS_MAX"
                step="1"
                :value="gridColumns"
                @input="setGridColumns($event.target.value)"
              />
              <div class="control__scale">
                <span>{{ COLUMNS_MIN }}</span>
                <span>{{ COLUMNS_MAX }}</span>
              </div>
            </div>

            <p class="hint">Los cambios se aplican automáticamente.</p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { onMounted, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import { useSettingsStore, COLUMNS_MIN, COLUMNS_MAX } from "@/stores/settings";

const emit = defineEmits(["close"]);

const props = defineProps({
  isOpen: { type: Boolean, required: true },
});

const settings = useSettingsStore();
const { crtIntensity, gridColumns } = storeToRefs(settings);
const { setCrtIntensity, setGridColumns } = settings;

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
  color: $text-3;
  font-family: "m6x11plus", monospace;
  font-size: 20px;
  cursor: pointer;
  transition: color 0.15s;
  &:hover {
    color: #e8443a;
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

/* Transición del modal (misma que AuthModal) */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
