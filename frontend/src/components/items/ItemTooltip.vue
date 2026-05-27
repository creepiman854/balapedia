<!--
  Tooltip flotante sobre una carta de item.

  Genérico para joker / consumible. Descripción coloreada por el
  mismo regex (sirve igual para tarots y planetas: +N Mult, $N, etc.).
  El badge inferior se resuelve por `getItemBadgeLabel`:
    - joker         → rareza (Común / Inusual / Raro / Legendario)
    - consumible    → tipo (Arcano / Planeta / Espectral)
-->
<template>
  <div :style="posStyle">
    <div v-if="isLocked" :style="lockedBoxStyle">
      <div :style="lockedHeaderStyle">
        <span :style="lockedHeaderTextStyle">Por descubrir</span>
      </div>
      <div :style="lockedBodyStyle">
        <p :style="lockedBodyTextStyle">{{ unlockText }}</p>
      </div>
    </div>

    <div v-else :style="boxStyle">
      <div :style="headerStyle">
        <span :style="headerTextStyle">{{ item.name }}</span>
      </div>
      <div :style="bodyStyle">
        <p :style="bodyTextStyle">
          <ColoredDescription :text="description" />
        </p>
      </div>
      <div v-if="badgeLabel" :style="footerStyle">
        <AccentBadge :label="badgeLabel" :color="accent.color" :glow="accent.glow" />
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

const accent = computed(() => getItemAccent(props.item));
const badgeLabel = computed(() => getItemBadgeLabel(props.item));

const unlockText = computed(
  () =>
    props.item.unlock_condition ||
    props.item.unlock_factor?.description ||
    "Compra o usa esta carta en una partida sin códigos para saber lo que hace.",
);

/**
 * `description` para jokers/decks/vouchers/packs, `effect` para card
 * modifiers (Enhancement/Edition/Seal). Mismo patrón explícito que
 * `displayEffect` en ItemDetailPanel:
 *   - cadena vacía o solo whitespace → "—"
 *   - cualquier otro caso → el texto resuelto
 *
 * Antes hacíamos `getItemEffectText(props.item) || '—'` pero quedaba
 * frágil: si el helper devolvía un placeholder con whitespace el OR
 * lógico no lo detectaba como vacío. Con el helper endurecido + este
 * computed explícito el bug de "el hover de MEJORAS sale como '—'" se
 * cierra definitivamente.
 */
const description = computed(() => {
  if (!props.item) return "—";
  const text = getItemEffectText(props.item);
  if (!text || (typeof text === "string" && !text.trim())) return "—";
  return text;
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
};
const lockedHeaderTextStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: "16px",
  color: TEAL.text2,
  letterSpacing: "0.5px",
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

// ── Desbloqueado ──
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
};
const footerStyle = {
  padding: "6px 10px 10px",
  display: "flex",
  justifyContent: "center",
};
</script>
