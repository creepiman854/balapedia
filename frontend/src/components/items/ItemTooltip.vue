<!--
  Tooltip flotante sobre una carta de item.

  Tres "kinds" soportados via prop:
    · 'unlockable' (default) → joker / consumable / deck / voucher /
       booster-pack / challenge-deck. Tiene rama `locked` (con
       "Por descubrir" + nombre atenuado) cuando isLocked.
    · 'blind' → metadata específica del blind (multiplicador de score,
       reward, ante). Sin rama locked.
    · 'tag' → metadata de Tag (ante mínimo, unlock condition opcional).
       Sin rama locked.

  Descripción coloreada por el mismo regex en los tres modos (sirve igual
  para tarots y planetas: +N Mult, $N, etc.).

  La variante bloqueada incluye el nombre real
  del item bajo "Por descubrir" en texto pequeño y atenuado. Permite
  identificar el item desde el tooltip y, lo más importante, permite al
  buscador encontrarlo por nombre aunque su imagen sea el dorso locked.
-->
<template>
  <div :style="posStyle">
    <!-- Rama "locked" (solo para kind=unlockable) -->
    <div v-if="kind === 'unlockable' && isLocked" :style="lockedBoxStyle">
      <div :style="lockedHeaderStyle">
        <span :style="lockedHeaderTextStyle">Undiscovered</span>
        <span v-if="item?.name" :style="lockedHiddenNameStyle">{{ item.name }}</span>
      </div>
      <div :style="lockedBodyStyle">
        <p :style="lockedBodyTextStyle">{{ unlockText }}</p>
      </div>
    </div>

    <!-- Rama "unlocked" / blind / tag -->
    <div v-else :style="boxStyle">
      <div :style="headerStyle">
        <span :style="headerTextStyle">{{ item.name }}</span>
      </div>
      <div :style="bodyStyle">
        <p :style="bodyTextStyle">
          <ColoredDescription :text="description" />
        </p>
      </div>
      <!-- Badge (solo unlockable: rareza/tipo) -->
      <div v-if="kind === 'unlockable' && badgeLabel" :style="footerStyle">
        <AccentBadge :label="badgeLabel" :color="accent.color" :glow="accent.glow" />
      </div>
      <!-- Metadata Blind: multiplicador + reward + ante -->
      <div v-else-if="kind === 'blind'" :style="metaBoxStyle">
        <div v-if="blindMultiplier" :style="metaLineStyle">
          <span :style="metaKeyStyle">Mult.</span>
          <span :style="metaValStyle">{{ blindMultiplier }}</span>
        </div>
        <div v-if="item.reward_money != null" :style="metaLineStyle">
          <span :style="metaKeyStyle">Reward</span>
          <span :style="metaValStyle">${{ item.reward_money }}</span>
        </div>
        <div v-if="blindAnte" :style="metaLineStyle">
          <span :style="metaKeyStyle">Ante</span>
          <span :style="metaValStyle">{{ blindAnte }}</span>
        </div>
      </div>
      <!-- Metadata Tag: ante + unlock condition -->
      <div v-else-if="kind === 'tag'" :style="metaBoxStyle">
        <div v-if="item.ante" :style="metaLineStyle">
          <span :style="metaKeyStyle">Ante</span>
          <span :style="metaValStyle">{{ item.ante }}</span>
        </div>
        <div v-if="item.unlock_condition" :style="unlockHintStyle">
          {{ item.unlock_condition }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { getItemAccent, getItemBadgeLabel, getItemEffectText } from "@/constants/items";
import AccentBadge from "@/components/common/AccentBadge.vue";
import ColoredDescription from "./ColoredDescription.vue";

const props = defineProps({
  item: { type: Object, required: true },
  isLocked: { type: Boolean, default: false },
  cardCenterX: { type: Number, required: true },
  cardTop: { type: Number, required: true },
  /**
   * Tipo de entidad. Determina qué metadata se muestra en el footer
   * y si la rama "locked" aplica.
   *   - 'unlockable' (default): jokers/decks/vouchers/etc.
   *   - 'blind': Blind (small/big/boss).
   *   - 'tag': Tag.
   */
  kind: {
    type: String,
    default: "unlockable",
    validator: (v) => ["unlockable", "blind", "tag"].includes(v),
  },
});

const TOOLTIP_W = 230;
const TEAL = {
  shadow: "#1E2E32",
  darkest: "#1A2A2E",
  dark: "#253C40",
  mid: "#3A5055",
  text2: "#A8C4C8",
};

const PIXEL_CLIP =
  "polygon(0px calc(100% - 12px), 3px calc(100% - 12px), 3px calc(100% - 6px), 6px calc(100% - 6px), 6px calc(100% - 3px), 12px calc(100% - 3px), 12px 100%, calc(100% - 12px) 100%, calc(100% - 12px) calc(100% - 3px), calc(100% - 6px) calc(100% - 3px), calc(100% - 6px) calc(100% - 6px), calc(100% - 3px) calc(100% - 6px), calc(100% - 3px) calc(100% - 12px), 100% calc(100% - 12px), 100% 12px, calc(100% - 3px) 12px, calc(100% - 3px) 6px, calc(100% - 6px) 6px, calc(100% - 6px) 3px, calc(100% - 12px) 3px, calc(100% - 12px) 0px, 12px 0px, 12px 3px, 6px 3px, 6px 6px, 3px 6px, 3px 12px, 0px 12px)";

const PIXEL_CLIP_SM =
  "polygon(0px calc(100% - 8px), 2px calc(100% - 8px), 2px calc(100% - 4px), 4px calc(100% - 4px), 4px calc(100% - 2px), 8px calc(100% - 2px), 8px 100%, calc(100% - 8px) 100%, calc(100% - 8px) calc(100% - 2px), calc(100% - 4px) calc(100% - 2px), calc(100% - 4px) calc(100% - 4px), calc(100% - 2px) calc(100% - 4px), calc(100% - 2px) calc(100% - 8px), 100% calc(100% - 8px), 100% 8px, calc(100% - 2px) 8px, calc(100% - 2px) 4px, calc(100% - 4px) 4px, calc(100% - 4px) 2px, calc(100% - 8px) 2px, calc(100% - 8px) 0px, 8px 0px, 8px 2px, 4px 2px, 4px 4px, 2px 4px, 2px 8px, 0px 8px)";

/**
 * Accent del tooltip:
 *   - unlockable → del item (rareza/tipo).
 *   - blind → por blind_type (small=blanco, big=naranja, boss=rojo).
 *   - tag → verde neutral.
 *
 * Centralizar la lógica aquí en lugar de llamar a getItemAccent cuando
 * no aplica evita ramas extras en el helper compartido y mantiene
 * cada kind autónomo en su renderizado.
 */
const accent = computed(() => {
  if (props.kind === "blind") {
    const t = String(props.item?.blind_type || "").toUpperCase();
    if (t === "SMALL") return { color: "#cfd6d8", glow: "rgba(207,214,216,0.4)" };
    if (t === "BIG") return { color: "#f59e0b", glow: "rgba(245,158,11,0.45)" };
    return { color: "#e84040", glow: "rgba(232,64,64,0.45)" }; // BOSS
  }
  if (props.kind === "tag") {
    return { color: "#22c55e", glow: "rgba(34,197,94,0.4)" };
  }
  // default: unlockable
  return getItemAccent(props.item);
});

const badgeLabel = computed(() => {
  if (props.kind !== "unlockable") return null;
  return getItemBadgeLabel(props.item);
});

const unlockText = computed(
  () =>
    props.item.unlock_condition ||
    props.item.unlock_factor?.description ||
    "Purchase or use this card in an unseeded run to learn what it does",
);

/**
 * Descripción a mostrar en el body. Mismo helper que el resto de la
 * app — fallback a "—" si está vacío.
 */
const description = computed(() => {
  if (!props.item) return "—";

  if (props.kind === "blind" || props.kind === "tag") {
    const text = props.item.description;
    if (!text || (typeof text === "string" && !text.trim())) return "—";
    return text;
  }

  // EXCEPCIÓN PARA CHALLENGE DECKS: Fallback si está vacío o tiene un guion
  if (String(props.item.type || "").toUpperCase() === "CHALLENGE_DECK") {
    const mod = props.item.modifier;
    if (!mod || mod.trim() === "-" || mod.trim() === "") {
      return "Has no rules or modifiers";
    }
    return mod;
  }

  const text = getItemEffectText(props.item);
  if (!text || (typeof text === "string" && !text.trim())) return "—";
  return text;
});

/**
 * Multiplicador del blind formateado con "x" y un decimal cuando hace
 * falta (Boss Blinds llegan a tener 1.5x / 2x). Si no hay valor o es 0,
 * no mostramos la línea.
 */
const blindMultiplier = computed(() => {
  if (props.kind !== "blind") return null;
  const m = props.item?.score_multiplier;
  if (m == null) return null;
  const num = Number(m);
  if (!Number.isFinite(num) || num === 0) return null;
  // Si es entero exacto, no añadimos decimal. Si tiene parte decimal,
  // mostramos un decimal (2.5x), nunca más (2.50x es ruido visual).
  const formatted = Number.isInteger(num) ? `${num}` : num.toFixed(1);
  return `x${formatted}`;
});

/**
 * Ante del blind. La fuente usa "Any" para los blinds que pueden
 * aparecer en cualquier ante, y un número como string ("8") para los
 * Finisher Blinds. Lo renderizamos tal cual.
 */
const blindAnte = computed(() => {
  if (props.kind !== "blind") return null;
  const a = props.item?.ante;
  if (!a) return null;
  return a === "8" ? "8 (Finisher)" : a;
});

const posStyle = computed(() => {
  const left = Math.max(
    8,
    Math.min(props.cardCenterX - TOOLTIP_W / 2, window.innerWidth - TOOLTIP_W - 8),
  );
  const bottom = window.innerHeight - props.cardTop + 10;
  return {
    position: "fixed",
    bottom: `${bottom}px`,
    left: `${left}px`,
    zIndex: 9000,
    width: `${TOOLTIP_W}px`,
    pointerEvents: "none",
    animation: "tooltipFadeIn 0.12s ease",
  };
});

// ── Bloqueado ──
const lockedBoxStyle = computed(() => ({
  background: TEAL.dark,
  clipPath: PIXEL_CLIP,
  filter: `drop-shadow(0 6px 20px ${TEAL.shadow})`,
  overflow: "hidden",
}));
const lockedHeaderStyle = {
  background: TEAL.mid,
  padding: "10px 12px",
  textAlign: "center",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "2px",
};
const lockedHeaderTextStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: "16px",
  color: TEAL.text2,
  letterSpacing: "0.5px",
};
const lockedHiddenNameStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: "11px",
  color: "rgba(168, 196, 200, 0.55)",
  letterSpacing: "0.3px",
  textTransform: "uppercase",
};
const lockedBodyStyle = {
  background: "#c8c8c8",
  margin: "6px",
  padding: "10px",
  clipPath: PIXEL_CLIP_SM,
};
const lockedBodyTextStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: "16px",
  color: "#2a2a2a",
  margin: 0,
  textAlign: "center",
  lineHeight: 1.5,
};

// ── Desbloqueado / Blind / Tag ──
const boxStyle = computed(() => ({
  background: TEAL.darkest,
  clipPath: PIXEL_CLIP,
  filter: `drop-shadow(0 6px 20px rgba(0,0,0,0.9)) drop-shadow(0 0 12px ${accent.value.glow})`,
  overflow: "hidden",
}));
const headerStyle = computed(() => ({
  background: TEAL.mid,
  padding: "10px 14px",
  textAlign: "center",
  borderBottom: `2px solid ${accent.value.color}30`,
}));
const headerTextStyle = computed(() => ({
  fontFamily: "'m6x11plus', monospace",
  fontSize: "16px",
  color: "#fff",
  letterSpacing: "0.5px",
  textShadow: `0 0 10px ${accent.value.color}`,
}));
const bodyStyle = {
  background: "#e8e4f0",
  margin: "6px",
  padding: "10px 12px",
  clipPath: PIXEL_CLIP_SM,
};
const bodyTextStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: "16px",
  color: "#1a1a1a",
  margin: 0,
  textAlign: "center",
  lineHeight: 1.6,
  whiteSpace: "pre-wrap",
};
const footerStyle = {
  padding: "6px 10px 10px",
  display: "flex",
  justifyContent: "center",
};

/**
 * Metadata box (blind / tag): bloque oscuro debajo del body con
 * líneas key/value sutiles (e.g. "Mult. — x1.5"). Mismo clip-path
 * pequeño que el body para coherencia visual.
 */
const metaBoxStyle = {
  background: TEAL.dark,
  margin: "0 6px 6px",
  padding: "6px 10px",
  clipPath: PIXEL_CLIP_SM,
  display: "flex",
  flexDirection: "column",
  gap: "2px",
};
const metaLineStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontFamily: "'m6x11plus', monospace",
  fontSize: "14px",
  color: TEAL.text2,
};
const metaKeyStyle = {
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  opacity: 0.75,
};
const metaValStyle = {
  color: "#fff",
  fontWeight: "bold",
};
const unlockHintStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: "14px",
  color: "rgba(168, 196, 200, 0.7)",
  fontStyle: "italic",
  marginTop: "4px",
  textAlign: "center",
  lineHeight: 1.3,
};
</script>
