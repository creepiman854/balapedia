<!--
  Modal de ajustes Balapedia.

  Tres controles:
    · CRT INTENSITY    0..100 % → settings.crtIntensity
    · MÚSICA           on/off  → settings.musicEnabled
        └─ VOLUMEN     0..100  (sólo visible si música ON) → settings.musicVolume
    · COLUMNAS GRID    5..15  → settings.gridColumns

  El modal vive ahora DENTRO de #app-content (ver App.vue), por lo que
  recibe los efectos CRT (aberración cromática, scanlines, vignette,
  curvatura del tubo). Como el barrel warp fue eliminado, las hitboxes
  de sliders y botones son 1:1 con su posición visual a cualquier
  intensidad.
-->
<template>
  <div class="settings-backdrop" @click.self="$emit('close')">
    <div class="settings-panel" role="dialog" aria-modal="true">
      <header class="settings-panel__head">
        <span class="settings-panel__title">⚙ AJUSTES</span>
        <span class="settings-panel__subtitle">Personaliza la experiencia</span>
      </header>

      <section class="settings-panel__body">
        <!-- CRT INTENSITY -->
        <div class="control">
          <div class="control__head">
            <span class="control__icon">📺</span>
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

        <!-- MÚSICA -->
        <div class="control">
          <div class="control__head">
            <span class="control__icon">🎵</span>
            <span class="control__label">Música de fondo</span>
            <button
              class="toggle"
              :data-on="musicEnabled ? '1' : '0'"
              role="switch"
              :aria-checked="musicEnabled"
              @click="setMusicEnabled(!musicEnabled)"
            >
              <i />
            </button>
          </div>
          <div v-if="musicEnabled" class="control__sub">
            <div class="control__head control__head--sub">
              <span class="control__icon">🔊</span>
              <span class="control__label">Volumen</span>
              <span class="control__value">{{ Math.round(musicVolume * 100) }}%</span>
            </div>
            <input
              class="slider"
              type="range"
              min="0"
              max="100"
              step="1"
              :value="Math.round(musicVolume * 100)"
              @input="setMusicVolume($event.target.value / 100)"
            />
            <p class="control__hint">
              Reproductor de música pendiente — el toggle queda persistido
              para cuando lo conectemos.
            </p>
          </div>
        </div>

        <!-- COLUMNAS GRID -->
        <div class="control">
          <div class="control__head">
            <span class="control__icon">▦</span>
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
      </section>

      <footer class="settings-panel__foot">
        <button class="close-btn" @click="$emit('close')">CERRAR</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { useSettingsStore, COLUMNS_MIN, COLUMNS_MAX } from '@/stores/settings'

const emit = defineEmits(['close'])

const settings = useSettingsStore()
// COLUMNS_MIN y COLUMNS_MAX se importan COMO NÚMEROS desde el módulo,
// NO desde storeToRefs (que los envolvía como refs y rompía <input :min>).
const { crtIntensity, musicEnabled, musicVolume, gridColumns } = storeToRefs(settings)
const { setCrtIntensity, setMusicEnabled, setMusicVolume, setGridColumns } = settings

function handleEsc(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', handleEsc))
onBeforeUnmount(() => window.removeEventListener('keydown', handleEsc))
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.settings-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.78);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.settings-panel {
  background: $panel-mid;
  width: 380px;
  max-width: calc(100vw - 32px);
  filter: drop-shadow(0 20px 60px $shadow);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  @include pixel-clip;

  &__head {
    background: $panel-dark;
    padding: 16px 20px;
    text-align: center;
    border-bottom: 2px solid $panel-medlight;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  &__title {
    font-family: 'm6x11plus', monospace;
    font-size: 16px;
    color: $text-1;
    letter-spacing: 1px;
  }
  &__subtitle {
    font-family: 'm6x11plus', monospace;
    font-size: 11px;
    color: $text-3;
  }

  &__body {
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  &__foot {
    padding: 0 20px 16px;
  }
}

.control {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__head {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'm6x11plus', monospace;
    font-size: 13px;
    color: $text-1;

    &--sub {
      margin-top: 6px;
    }
  }

  &__icon {
    font-size: 16px;
    flex-shrink: 0;
  }

  &__label {
    flex: 1;
  }

  &__value {
    font-family: 'm6x11plus', monospace;
    font-size: 13px;
    color: $text-2;
    min-width: 40px;
    text-align: right;
  }

  &__hint {
    font-family: 'm6x11plus', monospace;
    font-size: 10px;
    color: $text-3;
    line-height: 1.4;
    margin: 0;
  }

  &__sub {
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.18);
    display: flex;
    flex-direction: column;
    gap: 6px;
    @include pixel-clip-sm;
  }

  &__scale {
    display: flex;
    justify-content: space-between;
    font-family: 'm6x11plus', monospace;
    font-size: 10px;
    color: $text-3;
    padding: 0 2px;
  }
}

.slider {
  appearance: none;
  -webkit-appearance: none;
  width: 100%;
  height: 6px;
  background: $panel-darkest;
  outline: none;
  cursor: pointer;
  @include pixel-clip-sm;

  &::-webkit-slider-thumb {
    appearance: none;
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    background: $text-1;
    cursor: pointer;
    border: 2px solid $panel-medlight;
  }
  &::-moz-range-thumb {
    width: 16px;
    height: 16px;
    background: $text-1;
    border: 2px solid $panel-medlight;
    cursor: pointer;
  }
}

.toggle {
  width: 44px;
  height: 22px;
  background: $panel-darkest;
  border: 1px solid $panel-medlight;
  position: relative;
  cursor: pointer;
  transition: background 0.15s;
  padding: 0;
  @include pixel-clip-sm;

  i {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    background: $text-1;
    transition: transform 0.15s;
  }

  &[data-on='1'] {
    background: #1a4030;
    border-color: #22c55e;
    i {
      transform: translateX(22px);
      background: #22c55e;
    }
  }
}

.close-btn {
  width: 100%;
  font-family: 'm6x11plus', monospace;
  font-size: 13px;
  color: #fff;
  background: $panel-dark;
  border: 1px solid $panel-medlight;
  padding: 12px 0;
  cursor: pointer;
  letter-spacing: 0.5px;
  transition: filter 0.15s;
  @include pixel-clip;

  &:hover {
    filter: brightness(1.3);
  }
}
</style>
