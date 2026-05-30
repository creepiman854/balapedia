<!--
  Carta visual de un Tag (recompensa por skip de Small/Big Blind).

  Independiente de ItemCard / ItemCardArt: los Tags no son Unlockable,
  no llevan tilt 3D ni stickers, ni estado locked. Solo imagen + nombre
  + hover effect verde sutil.

  El hover muestra la descripción a través del ItemTooltip global
  (kind="tag"); el parent dispara el flotante via @hover. En móvil/
  tablet el tooltip está oculto y la información se sirve mediante el
  bottom-sheet del ItemDetailPanel (el parent debe escuchar @select).
-->
<template>
  <div
    class="tag-card"
    :class="{ 'tag-card--selected': isSelected }"
    @click="emit('select', item)"
    @mouseenter="onEnter"
    @mouseleave="emit('leave')"
  >
    <div class="tag-card__art-wrap" v-tilt="{ max: 20, scale: 1.08, speed: 300 }">
      <img
        v-if="item.image_url"
        :src="item.image_url"
        :alt="item.name"
        class="tag-card__art"
        draggable="false"
        loading="lazy"
      />
      <div v-else class="tag-card__art-fallback">{{ initial }}</div>
    </div>

    <div class="tag-card__name">{{ item.name }}</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  item: { type: Object, required: true },
  isSelected: { type: Boolean, default: false },
});

const emit = defineEmits(["select", "hover", "leave"]);

const initial = computed(() => (props.item?.name || "?").trim()[0]?.toUpperCase() || "?");

function onEnter(e) {
  emit("hover", { item: props.item, target: e.currentTarget });
}
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.tag-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 8px 12px;
  background: rgba(0, 0, 0, 0.28);
  cursor: pointer;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    filter 0.18s ease;
  @include pixel-clip;

  @include can-hover {
    &:hover {
      transform: translateY(-3px);
      filter: brightness(1.1);
      box-shadow: 0 0 16px rgba(34, 197, 94, 0.4);
    }
  }
  &--selected {
    background: rgba(34, 197, 94, 0.12);
  }
}

.tag-card__art-wrap {
  width: 72px;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tag-card__art {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
  filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.55));
  transition: transform 0.18s ease;
}

@include can-hover {
  .tag-card:hover .tag-card__art {
    transform: scale(1.07);
  }
}

.tag-card__art-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $panel-mid;
  font-family: "m6x11plus", monospace;
  font-size: 24px;
  color: $panel-light;
  @include pixel-clip-sm;
}

.tag-card__name {
  font-family: "m6x11plus", monospace;
  font-size: 17px;
  color: #fff;
  text-align: center;
  letter-spacing: 0.4px;
  text-shadow: 0 2px 0 rgba(0, 0, 0, 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* ──────────────────────────────────────────────────────────────
 * TABLET — escalonamos un punto las medidas para que más tags
 * entren por fila manteniendo la legibilidad.
 * ────────────────────────────────────────────────────────────── */
@include tablet {
  .tag-card {
    padding: 8px 6px 10px;
    gap: 4px;
  }
  .tag-card__art-wrap {
    width: 58px;
  }
  .tag-card__name {
    font-size: 14px;
  }
  .tag-card__art-fallback {
    font-size: 20px;
  }
}

/* ──────────────────────────────────────────────────────────────
 * MOBILE — apretamos al máximo manteniendo aspect-ratio cuadrado
 * del arte. El truncado del nombre evita layouts inconsistentes.
 * ────────────────────────────────────────────────────────────── */
@include mobile {
  .tag-card {
    padding: 6px 4px 8px;
    gap: 3px;
  }
  .tag-card__art-wrap {
    width: 46px;
  }
  .tag-card__name {
    font-size: 12px;
    letter-spacing: 0.2px;
  }
  .tag-card__art-fallback {
    font-size: 16px;
  }
}
</style>
