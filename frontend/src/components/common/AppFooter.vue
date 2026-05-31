<template>
  <div class="footer-wrapper" :class="{ 'is-open': isOpen }">
    <!-- Pestaña para desplegar/ocultar -->
    <button
      class="footer-toggle"
      @click="$emit('toggle')"
      :title="isOpen ? 'Close credits' : 'Show credits'"
    >
      <iconify-icon :icon="isOpen ? 'pixel:chevron-down' : 'pixel:chevron-up'" noobserver />
      <span v-if="!isOpen">CREDITS</span>
    </button>

    <!-- Contenido del Footer -->
    <footer class="app-footer">
      <div class="footer-content">
        <div class="footer-section">
          <p>
            An
            <a
              href="https://github.com/creepiman854/balapedia"
              target="_blank"
              rel="noopener noreferrer"
              class="highlight-link"
              >Open-Source</a
            >
            project.
          </p>
          <div class="creator">
            <span>Created by</span>
            <a
              href="https://github.com/creepiman854"
              target="_blank"
              rel="noopener noreferrer"
              class="github-link"
            >
              <iconify-icon icon="pixel:github" noobserver />
              Creepi (creepiman854)
            </a>
          </div>
        </div>

        <div class="footer-section disclaimer">
          <p>
            Data sourced from
            <a href="https://balatrowiki.org" target="_blank" rel="noopener noreferrer"
              >balatrowiki.org</a
            >.
          </p>
          <p>
            Balapedia is an unofficial companion app not affiliated with
            <strong>LocalThunk</strong> or Playstack.
            <br />
            Please support the official release:
            <a
              href="https://store.steampowered.com/app/2379780/Balatro/"
              target="_blank"
              rel="noopener noreferrer"
              class="buy-link"
            >
              Buy Balatro
            </a>
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["toggle"]);
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.footer-wrapper {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 5000;
  /* Oculta el footer empujándolo hacia abajo el 100% de su propia altura */
  transform: translateY(100%);
  transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);

  &.is-open {
    transform: translateY(0);
  }
}

.footer-toggle {
  position: absolute;
  top: -34px;
  left: 50%;
  transform: translateX(-50%);
  height: 34px;
  padding: 0 16px;
  background: $panel-dark;
  color: $text-2;
  font-family: "m6x11plus", monospace;
  font-size: 14px;
  letter-spacing: 1px;

  /* Quita el borde nativo y el border-radius */
  border: none;
  border-radius: 0;

  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;

  /* Aplica el nuevo clip-path (esquinas de arriba) */
  @include pixel-clip-top-only;

  transition:
    color 0.15s,
    background 0.15s;

  iconify-icon {
    font-size: 16px;
  }

  @include can-hover {
    &:hover {
      background: $panel-mid;
      color: $text-1;
    }
  }

  @include mobile {
    display: none;
  }
}

/* Si el footer está abierto, mostramos la pestaña en móvil para poder cerrarlo */
.footer-wrapper.is-open .footer-toggle {
  @include mobile {
    display: flex;
  }
}

.app-footer {
  background: linear-gradient(0deg, $panel-dark 0%, $shadow 100%);
  border-top: 2px solid $panel-mid;
  padding: 24px 16px;
  color: $text-2;
  font-family: "m6x11plus", monospace;
  font-size: 15px;
  text-align: center;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.8);
}

.footer-content {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  align-items: center;

  @include tablet {
    flex-direction: row;
    justify-content: space-between;
    text-align: left;
  }
}

.footer-section {
  display: flex;
  flex-direction: column;
  gap: 8px;

  p {
    margin: 0;
    line-height: 1.4;
  }
}

.highlight-link {
  color: #2563eb;
  text-decoration: none;
  transition: filter 0.15s;

  @include can-hover {
    &:hover {
      filter: brightness(1.3);
      text-decoration: underline;
    }
  }
}

.creator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  @include tablet {
    justify-content: flex-start;
  }
}

.github-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #fff;
  background: $panel-mid;
  padding: 6px 10px;
  text-decoration: none;
  transition:
    transform 0.1s,
    background 0.15s;
  @include pixel-clip;

  iconify-icon {
    font-size: 18px;
  }

  @include can-hover {
    &:hover {
      background: lighten($panel-mid, 10%);
      transform: scale(1.04);
    }
  }

  &:active {
    transform: scale(0.96);
  }
}

.disclaimer {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);

  a {
    color: rgba(255, 255, 255, 0.7);
    text-decoration: underline;

    @include can-hover {
      &:hover {
        color: #fff;
      }
    }
  }

  .buy-link {
    color: #dc2626;
    font-weight: bold;
    text-decoration: none;

    @include can-hover {
      &:hover {
        filter: brightness(1.3);
        text-decoration: underline;
      }
    }
  }
}
</style>
