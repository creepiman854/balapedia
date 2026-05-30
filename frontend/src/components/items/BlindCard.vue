<!--
  Carta visual de un Blind (Small / Big / Boss).

  Independiente de ItemCard / ItemCardArt — los Blinds no son
  Unlockable, no llevan tilt 3D ni stickers, ni cambian de imagen entre
  estados locked/unlocked. Solo imagen + nombre + chip de multiplicador
  + reward, con hover effect coloreado por tipo.

  Prop `variant`:
    - 'hero' → tile destacado de la fila superior (3 en horizontal:
       Small / Big / Boss). Más grande, con etiqueta de score arriba
       y reward debajo. Pensada para la fila tipo "apuesta inicial".
    - 'grid' → tile reducido para el grid de Boss Blinds individuales
       debajo de la fila hero. Mismo aspect-ratio pero más pequeño,
       el chip de multiplicador queda como overlay esquina.

  Hover effect: pequeño zoom + glow del color del blind_type.

  El parent emite `select` y `hover` para el flotante ItemTooltip
  global, mismo patrón que ItemCard. En móvil/tablet el tooltip está
  oculto y la información se sirve mediante el bottom-sheet del
  ItemDetailPanel (el parent debe escuchar @select).
-->
<template>
  <div
    class="blind-card"
    :class="[
      `blind-card--${blindClass}`,
      `blind-card--${variant}`,
      { 'blind-card--selected': isSelected },
    ]"
    @click="emit('select', item)"
    @mouseenter="onEnter"
    @mouseleave="emit('leave')"
  >
    <div class="blind-card__art-wrap" v-tilt="{ max: 20, scale: 1.05, speed: 300 }">
      <img
        v-if="item.image_url"
        :src="item.image_url"
        :alt="item.name"
        class="blind-card__art"
        draggable="false"
        loading="lazy"
      />

      <!-- Chip de multiplicador (overlay esquina superior izquierda) -->
      <div v-if="multiplierLabel" class="blind-card__mult">{{ multiplierLabel }}</div>

      <!-- Finisher marker (Boss con ante=8) -->
      <div v-if="isFinisher" class="blind-card__finisher" title="Finisher Blind">
        <iconify-icon icon="pixel:star-solid" noobserver />
      </div>
    </div>

    <div class="blind-card__name">{{ item.name }}</div>

    <!-- Reward (solo en variante hero — el grid evita el ruido visual) -->
    <div v-if="variant === 'hero' && item.reward_money != null" class="blind-card__reward">
      <span class="blind-card__reward-icon">$</span>
      <span>{{ item.reward_money }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  item: { type: Object, required: true },
  isSelected: { type: Boolean, default: false },
  variant: {
    type: String,
    default: "grid",
    validator: (v) => ["hero", "grid"].includes(v),
  },
});

const emit = defineEmits(["select", "hover", "leave"]);

// Mapeamos 'showdown' a 'boss' para que herede el CSS rojo y el hover
const blindClass = computed(() => {
  const t = String(props.item?.blind_type || "boss").toLowerCase();
  return t === "showdown" ? "boss" : t;
});

// La estrellita de Finisher ahora se basa en SHOWDOWN
const isFinisher = computed(() => {
  return String(props.item?.blind_type || "").toUpperCase() === "SHOWDOWN";
});

/**
 * "x1.5" / "x2" — multiplicador del score requerido. Si es 1 (Small)
 * no lo mostramos para no inundar la UI con info trivial.
 */
const multiplierLabel = computed(() => {
  const m = Number(props.item?.score_multiplier);
  if (!Number.isFinite(m) || m === 0 || m === 1) return null;
  return `x${Number.isInteger(m) ? m : m.toFixed(1)}`;
});

function onEnter(e) {
  emit("hover", { item: props.item, target: e.currentTarget });
}
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.blind-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 10px 14px;
  background: rgba(0, 0, 0, 0.28);
  cursor: pointer;
  transition:
    transform 0.18s ease,
    background 0.18s ease,
    filter 0.18s ease;
  @include pixel-clip;

  @include can-hover {
    &:hover {
      transform: translateY(-3px);
      filter: brightness(1.1);
    }
  }
  &--selected {
    background: rgba(0, 0, 0, 0.4);
  }
}

/* ── Variantes de tamaño ────────────────────────────────────────── */
.blind-card--hero {
  padding: 18px 14px 18px;
  gap: 10px;
}
.blind-card--hero .blind-card__art-wrap {
  width: 104px;
}
.blind-card--hero .blind-card__name {
  font-size: 20px;
}

.blind-card--grid .blind-card__art-wrap {
  width: 76px;
}
.blind-card--grid .blind-card__name {
  font-size: 17px;
}

/* ── Color por blind_type ───────────────────────────────────────── */
.blind-card--small {
  @include can-hover {
    &:hover {
      box-shadow: 0 0 18px rgba(207, 214, 216, 0.35);
    }
  }
}
.blind-card--big {
  @include can-hover {
    &:hover {
      box-shadow: 0 0 18px rgba(245, 158, 11, 0.5);
    }
  }
  .blind-card__mult {
    background: rgba(245, 158, 11, 0.9);
    color: #2a1908;
  }
}
.blind-card--boss {
  @include can-hover {
    &:hover {
      box-shadow: 0 0 18px rgba(232, 64, 64, 0.5);
    }
  }
  .blind-card__mult {
    background: rgba(232, 64, 64, 0.92);
    color: #fff;
  }
}

/* ── Arte (image + overlays) ────────────────────────────────────── */
.blind-card__art-wrap {
  position: relative;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.blind-card__art {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
  filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.55));
  transition: transform 0.18s ease;
}

@include can-hover {
  .blind-card:hover .blind-card__art {
    transform: scale(1.06);
  }
}

/* Chip de multiplicador (esquina superior izquierda) */
.blind-card__mult {
  position: absolute;
  top: -6px;
  left: -6px;
  padding: 2px 6px;
  font-family: "m6x11plus", monospace;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.5px;
  @include pixel-clip-sm;
  z-index: 1;
}

/* Marca de Finisher (estrella esquina superior derecha) */
.blind-card__finisher {
  display: flex;
  align-items: center;
  position: absolute;
  top: -4px;
  right: -2px;
  font-family: "m6x11plus", monospace;
  font-size: 16px;
  color: #f0a020;
  text-shadow: 0 0 6px rgba(240, 160, 32, 0.7);
  z-index: 1;
  pointer-events: none;
}

.blind-card__name {
  font-family: "m6x11plus", monospace;
  color: #fff;
  text-align: center;
  letter-spacing: 0.4px;
  text-shadow: 0 2px 0 rgba(0, 0, 0, 0.6);
  /* Truncado a 2 líneas para evitar saltos de altura inconsistentes
   * cuando nombres como "The Tooth" conviven con "The Pillar of Salt". */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.blind-card__reward {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: "m6x11plus", monospace;
  font-size: 16px;
  color: #f0b030;
  letter-spacing: 0.3px;
}
.blind-card__reward-icon {
  font-weight: 700;
}

/* ──────────────────────────────────────────────────────────────
 * TABLET — reducimos arte, padding y tipografía un escalón para
 * que entren más Boss Blinds por fila sin perder legibilidad.
 * ────────────────────────────────────────────────────────────── */
@include tablet {
  .blind-card {
    padding: 10px 8px 12px;
    gap: 5px;
  }
  .blind-card--hero {
    padding: 14px 12px;
    gap: 8px;
  }
  .blind-card--hero .blind-card__art-wrap {
    width: 84px;
  }
  .blind-card--hero .blind-card__name {
    font-size: 17px;
  }

  .blind-card--grid .blind-card__art-wrap {
    width: 62px;
  }
  .blind-card--grid .blind-card__name {
    font-size: 14px;
  }

  .blind-card__mult {
    font-size: 12px;
    padding: 2px 5px;
  }
  .blind-card__finisher {
    font-size: 14px;
  }
  .blind-card__reward {
    font-size: 14px;
  }
}

/* ──────────────────────────────────────────────────────────────
 * MOBILE — apretamos un poco más. La estrella de Finisher y el
 * chip de multiplicador siguen siendo visibles pero más sutiles.
 * ────────────────────────────────────────────────────────────── */
@include mobile {
  .blind-card {
    padding: 8px 6px 10px;
    gap: 4px;
  }
  .blind-card--hero {
    padding: 10px 8px;
    gap: 6px;
  }
  .blind-card--hero .blind-card__art-wrap {
    width: 66px;
  }
  .blind-card--hero .blind-card__name {
    font-size: 14px;
  }

  .blind-card--grid .blind-card__art-wrap {
    width: 50px;
  }
  .blind-card--grid .blind-card__name {
    font-size: 12px;
  }

  .blind-card__mult {
    font-size: 11px;
    padding: 1px 4px;
    top: -4px;
    left: -4px;
  }
  .blind-card__finisher {
    font-size: 12px;
    top: -2px;
    right: -1px;
  }
  .blind-card__reward {
    font-size: 13px;
  }
}
</style>
