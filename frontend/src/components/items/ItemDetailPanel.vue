<!--
  Panel derecho con el detalle del item seleccionado.

  Genérico para joker / consumable / deck / voucher / booster-pack /
  challenge-deck. Las secciones que no aplican a un tipo concreto se
  ocultan con v-if:
    - RAREZA / TIPO → siempre una (rareza si es joker; tipo si es
      consumable), nunca ambas.
    - EFECTO → siempre (la descripción).
    - DESBLOQUEO → si hay unlock_condition o unlock_factor.
    - CHALLENGE DECK (4 secciones) → solo si itemType === 'CHALLENGE_DECK':
      MODIFICADOR, INICIO, BANEADO, BARAJA BASE.
    - ESTADÍSTICAS → buy/sell (jokers/consumables/vouchers) o COSTE
      (booster packs). effect_type/activation solo si jokers.
    - COMPATIBILIDAD → solo si alguno de is_copyable/perishable/eternal
      es true (jokers).

  Botón unlock/re-lock (Fase 2):
    Toggle bidireccional. El padre emite `manual-unlock` con
    `(item, unlocked)` y elige qué servicio llamar.
-->
<template>
  <div v-if="!item" class="empty">
    <div class="empty__icon">?</div>
    <p class="empty__text">Select an item<br />to view the<br />details</p>
  </div>

  <div v-else class="detail">
    <!-- Arte -->
    <div class="detail__art-wrap">
      <div v-tilt="{ max: 10, scale: 1.04, speed: 400 }" class="detail__art">
        <ItemCardArt :item="item" :is-locked="isLocked" :is-selected="false" :accent="accent" />
      </div>
      <!-- Solo para jokers y decks autenticados -->
      <StakeSelector
        v-if="
          isAuthenticated &&
          !isLocked &&
          (itemType === 'JOKER' || itemType === 'DECK' || itemType === 'CHALLENGE_DECK')
        "
        :item="item"
        @set-stake="onSetStake"
      />
    </div>

    <div class="detail__body">
      <!-- Botón unlock (cuando bloqueado) o re-lock (cuando desbloqueado). No aparece en Challege Deck -->
      <div
        v-if="isAuthenticated && isLocked && canUnlock && itemType !== 'CHALLENGE_DECK'"
        class="stroke-wrapper manual-unlock-wrapper"
      >
        <button class="manual-unlock" :disabled="busy" @click="onToggleUnlock(true)">
          {{ busy ? "Unlocking..." : "Mark as unlocked" }}
        </button>
      </div>
      <div
        v-else-if="
          isAuthenticated && !isLocked && canUnlock && isRelockable && itemType !== 'CHALLENGE_DECK'
        "
        class="stroke-wrapper manual-relock-wrapper"
      >
        <button class="manual-relock" :disabled="busy" @click="onToggleUnlock(false)">
          {{ busy ? "Locking..." : "Lock again" }}
        </button>
      </div>

      <!-- EFECTO -->
      <section class="section">
        <header
          class="section__head"
          :style="{ borderLeftColor: itemType === 'CHALLENGE_DECK' ? '#8b5cf6' : accent.color }"
        >
          <span class="section__icon">
            <iconify-icon
              :icon="itemType === 'CHALLENGE_DECK' ? 'pixel:warning' : 'pixel:bolt-solid'"
              noobserver
            />
          </span>
          <span :style="{ color: itemType === 'CHALLENGE_DECK' ? '#8b5cf6' : accent.color }">
            {{ itemType === "CHALLENGE_DECK" ? "RULES & MODIFIERS" : "EFFECT" }}
          </span>
        </header>
        <div class="section__body">
          <div
            class="stroke-wrapper"
            :style="{
              '--stroke-color': itemType === 'CHALLENGE_DECK' ? '#8b5cf640' : `${accent.color}40`,
            }"
          >
            <div
              class="effect-box"
              :style="{
                '--tint-color': itemType === 'CHALLENGE_DECK' ? '#8b5cf615' : `${accent.color}15`,
                color: isLocked
                  ? '#4D6870'
                  : itemType === 'CHALLENGE_DECK'
                    ? '#8b5cf6'
                    : accent.color,
              }"
            >
              <ColoredDescription :text="displayEffect" />
            </div>
          </div>
        </div>
      </section>

      <!-- RAREZA / TIPO -->
      <section v-if="badgeLabel" class="section">
        <header class="section__head" :style="{ borderLeftColor: accent.color }">
          <span class="section__icon">◆</span>
          <span :style="{ color: accent.color }">{{ item.rarity ? "RARITY" : "TYPE" }}</span>
        </header>
        <div class="section__body section__body--center">
          <div :style="{ filter: `drop-shadow(0 0 8px ${accent.glow})` }">
            <AccentBadge :label="badgeLabel" :color="accent.color" :glow="accent.glow" />
          </div>
        </div>
      </section>

      <!-- DESBLOQUEO -->
      <section v-if="unlockText" class="section">
        <header class="section__head" style="border-left-color: #708387">
          <span class="section__icon"><iconify-icon icon="pixel:unlock" noobserver /></span>
          <span>UNLOCK REQUIREMENT</span>
        </header>
        <div class="section__body section__body--unlock">
          {{ unlockText }}
        </div>
      </section>

      <!--
        ── CHALLENGE DECK SECTIONS ──
        Cuatro bloques exclusivos del tipo CHALLENGE_DECK. Aparecen solo
        si el campo correspondiente tiene contenido (todos pueden ser
        NULL en BD salvo `modifier` que es required).
      -->
      <template v-if="itemType === 'CHALLENGE_DECK' && !isLocked">
        <section v-if="item.starter" class="section">
          <header class="section__head" style="border-left-color: #22c55e">
            <span class="section__icon"><iconify-icon icon="pixel:play-solid" noobserver /></span>
            <span style="color: #22c55e">STARTING CONDITIONS</span>
          </header>
          <div class="section__body section__body--challenge">
            <ColoredDescription :text="item.starter" />
          </div>
        </section>

        <section v-if="item.banned" class="section">
          <header class="section__head" style="border-left-color: #ef4444">
            <span class="section__icon"><iconify-icon icon="pixel:cross" noobserver /></span>
            <span style="color: #ef4444">RESTRICTIONS</span>
          </header>
          <div class="section__body section__body--challenge">
            <ColoredDescription :text="item.banned" />
          </div>
        </section>

        <section v-if="item.deck_description" class="section">
          <header class="section__head" style="border-left-color: #3b82f6">
            <span class="section__icon"><iconify-icon icon="pixel:card-solid" noobserver /></span>
            <span style="color: #3b82f6">BASE DECK</span>
          </header>
          <div class="section__body section__body--challenge">
            {{ item.deck_description }}
          </div>
        </section>
      </template>

      <!-- MEJORA A (vouchers base con next_voucher_id) -->
      <section v-if="item._nextVoucher" class="section">
        <header class="section__head" style="border-left-color: #3b82f6">
          <span class="section__icon">⬆</span>
          <span style="color: #3b82f6">UPGRADES TO</span>
        </header>
        <div class="section__body upgrade-box">
          <img
            v-if="item._nextVoucher.image_url"
            :src="item._nextVoucher.image_url"
            :alt="item._nextVoucher.name"
            class="upgrade-box__thumb"
            draggable="false"
          />
          <div v-else class="upgrade-box__thumb upgrade-box__thumb--missing">?</div>
          <span class="upgrade-box__name">{{ item._nextVoucher.name }}</span>
        </div>
      </section>

      <!-- ESTADÍSTICAS -->
      <section v-if="hasStats" class="section">
        <header class="section__head" style="border-left-color: #c09020">
          <span class="section__icon"><iconify-icon icon="pixel:notebook-solid" noobserver /></span>
          <span style="color: #c09020">STATS</span>
        </header>
        <div class="section__body stats">
          <!--
            Booster Packs solo tienen `cost`, no buy/sell. Mostramos un
            único bloque "COSTE" ocupando toda la fila para que la
            tarjeta no se vea desbalanceada con un solo precio.
          -->
          <div v-if="itemType === 'BOOSTER_PACK'" class="stats__row">
            <div class="stroke-wrapper stat-wrapper--buy stat-wrapper--full">
              <div class="stat stat--buy">
                <div class="stat__label">COST</div>
                <div class="stat__value">{{ formatPrice(item.cost) }}</div>
              </div>
            </div>
          </div>
          <!--
            Resto (jokers / consumables / vouchers): par COMPRA / VENTA
            como hasta ahora.
          -->
          <div v-else class="stats__row">
            <div class="stroke-wrapper stat-wrapper--buy">
              <div class="stat stat--buy">
                <div class="stat__label">BUY PRICE</div>
                <div class="stat__value">{{ formatPrice(item.buy_price) }}</div>
                <div v-if="item.in_shop === false" class="stat__sublabel">
                  (cannot be found in shop)
                </div>
              </div>
            </div>
            <div class="stroke-wrapper stat-wrapper--sell">
              <div class="stat stat--sell">
                <div class="stat__label">SELL PRICE</div>
                <div class="stat__value">{{ formatPrice(item.sell_price) }}</div>
              </div>
            </div>
          </div>
          <div v-if="hasEffectMeta" class="stats__row">
            <div v-if="item.effect_type" class="stat stat--info">
              <div class="stat__label">TYPE</div>
              <div class="stat__value stat__value--sm">{{ item.effect_type }}</div>
            </div>
            <div v-if="item.activation" class="stat stat--info">
              <div class="stat__label">ACTIVATION</div>
              <div class="stat__value stat__value--sm">{{ item.activation }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- COMPATIBILIDAD -->
      <section v-if="hasCompat" class="section">
        <header class="section__head" style="border-left-color: #708387">
          <span class="section__icon"><iconify-icon icon="pixel:cog-solid" noobserver /></span>
          <span>COMPATIBILITY</span>
        </header>
        <div class="section__body compat">
          <div v-if="item.is_copyable" class="stroke-wrapper compat-wrapper--copy">
            <div class="compat__tile compat__tile--copy">
              <div class="compat__symbol"><iconify-icon icon="pixel:copy" noobserver /></div>
              <div class="compat__label">Copyable</div>
            </div>
          </div>
          <div v-if="item.is_perishable" class="stroke-wrapper compat-wrapper--perish">
            <div class="compat__tile compat__tile--perish">
              <div class="compat__symbol"><iconify-icon icon="pixel:clock" noobserver /></div>
              <div class="compat__label">PERISHABLE</div>
            </div>
          </div>
          <div v-if="item.is_eternal" class="stroke-wrapper compat-wrapper--eternal">
            <div class="compat__tile compat__tile--eternal">
              <div class="compat__symbol">
                <iconify-icon icon="famicons:infinite-sharp" noobserver />
              </div>
              <div class="compat__label">ETERNAL</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { getItemAccent, getItemBadgeLabel, getItemEffectText } from "@/constants/items";
import ItemCardArt from "./ItemCardArt.vue";
import AccentBadge from "@/components/common/AccentBadge.vue";
import ColoredDescription from "./ColoredDescription.vue";
import StakeSelector from "./StakeSelector.vue";
import { useAuthStore } from "@/stores/auth";
import { storeToRefs } from "pinia";
import { setStickerApplication } from "@/services/progression";

const props = defineProps({
  item: { type: Object, default: null },
  isLocked: { type: Boolean, default: false },
  /**
   * Si true, muestra el botón de unlock/relock cuando aplique.
   * Para jokers/decks/vouchers/packs/challenges va a true; para card
   * modifiers, false (no son Unlockable).
   */
  canUnlock: { type: Boolean, default: false },
});

const emit = defineEmits(["manual-unlock", "stake-updated"]);

const itemType = computed(() => String(props.item?.type || "").toUpperCase());
const updatingStake = ref(false);

const authStore = useAuthStore();
const { isAuthenticated } = storeToRefs(authStore);

const busy = ref(false);

const accent = computed(() => (props.item ? getItemAccent(props.item) : {}));
const badgeLabel = computed(() => getItemBadgeLabel(props.item));

const displayEffect = computed(() => {
  if (props.isLocked) return "???";

  if (itemType.value === "CHALLENGE_DECK") {
    const mod = props.item.modifier;
    // Fallback dinámico para descripciones vacías o guiones
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
 * `hasStats` ahora reconoce también `cost` (Booster Packs) además de
 * los pares buy/sell que ya tenía. effect_type/activation siguen
 * disparando la sección por simetría con el comportamiento previo.
 */
const hasStats = computed(
  () =>
    props.item &&
    (props.item.buy_price != null ||
      props.item.sell_price != null ||
      props.item.cost != null ||
      props.item.effect_type ||
      props.item.activation),
);

const hasEffectMeta = computed(
  () => props.item && (props.item.effect_type || props.item.activation),
);

const hasCompat = computed(
  () => props.item && (props.item.is_copyable || props.item.is_perishable || props.item.is_eternal),
);

const unlockText = computed(() => {
  if (!props.item) return "";
  return props.item.unlock_condition || props.item.unlock_factor?.description || "";
});

/**
 * "Es re-lockeable" = el item tiene una condición de desbloqueo real,
 * no es "Available from start". Items disponibles desde el inicio no
 * tienen estado bloqueado al que volver.
 */
const isRelockable = computed(() => {
  if (!props.item) return false;

  // Intercepción: Los 5 primeros Challenge Decks no se pueden bloquear
  if (itemType.value === "CHALLENGE_DECK") {
    const defaultUnlocked = [
      "THE OMELETTE",
      "15 MINUTE CITY",
      "RICH GET RICHER",
      "ON A KNIFE'S EDGE",
      "X-RAY VISION",
    ];
    if (defaultUnlocked.includes(String(props.item.name || "").toUpperCase())) {
      return false;
    }
  }

  const condition = String(
    props.item.unlock_condition || props.item.unlock_factor?.description || "",
  )
    .trim()
    .toLowerCase();
  if (!condition) return false;
  if (
    condition.includes("available from start") ||
    condition.includes("available from the start") ||
    condition.includes("disponible desde el inicio")
  ) {
    return false;
  }
  const code = String(props.item.unlock_factor?.code || "").toLowerCase();
  if (code === "available_from_start" || code === "start") return false;
  return true;
});

function formatPrice(v) {
  if (!Number.isFinite(Number(v))) return "—";
  return `$${Number(v)}`;
}

/**
 * Toggle unificado: emite `manual-unlock` con dos argumentos
 * (item, unlocked) para que la vista padre llame al servicio
 * adecuado. El `busy` local evita doble click; un setTimeout corto al
 * final relaja el estado por si el padre no actualiza la prop locked
 * de forma síncrona (e.g. error de red).
 */
async function onToggleUnlock(unlocked) {
  if (busy.value || !props.item) return;
  busy.value = true;
  try {
    emit("manual-unlock", props.item, unlocked);
  } finally {
    setTimeout(() => (busy.value = false), 800);
  }
}

async function onSetStake(stakeOrder) {
  if (!props.item || updatingStake.value) return;
  updatingStake.value = true;

  try {
    const result = await setStickerApplication(props.item.id, stakeOrder);
    if (result && result.highest_stake_order !== undefined) {
      emit("stake-updated", {
        id: props.item.id,
        highest_stake_order: result.highest_stake_order,
      });
    }
  } catch (e) {
    console.error("[ItemDetailPanel] set-stake failed:", e);
    alert(
      "The sticker could not be applied: " +
        (e.response?.data?.message || e.message || "Server error"),
    );
  } finally {
    updatingStake.value = false;
  }
}
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

/* Wrapper dinámico para pixel-stroke que lee la variable --stroke-color */
.stroke-wrapper {
  display: flex;
  @include pixel-stroke(var(--stroke-color));
  transition: filter 0.15s;

  & > * {
    flex: 1;
  }

  &.manual-unlock-wrapper {
    --stroke-color: #22c55e;
    margin-top: 4px;
    margin-bottom: 12px;
  }
  &.manual-relock-wrapper {
    --stroke-color: #ef4444;
    margin-top: 4px;
    margin-bottom: 12px;
  }

  &.stat-wrapper--buy {
    --stroke-color: rgba(192, 144, 32, 0.9);
    flex: 1;
  }
  &.stat-wrapper--sell {
    --stroke-color: rgba(64, 128, 32, 0.9);
    flex: 1;
  }
  /*
   * Variante "full" para cuando solo hay UN stat-wrapper en la fila
   * (booster packs con COSTE). Sin flex: 1 colaboraría con otro
   * hermano, pero como hijo único debería ocupar el 100%.
   */
  &.stat-wrapper--full {
    flex: 1;
  }

  &.compat-wrapper--copy {
    --stroke-color: rgba(32, 192, 80, 0.9);
    flex: 1;
    min-width: 72px;
  }
  &.compat-wrapper--perish {
    --stroke-color: rgba(224, 128, 32, 0.9);
    flex: 1;
    min-width: 72px;
  }
  &.compat-wrapper--eternal {
    --stroke-color: rgba(96, 128, 224, 0.9);
    flex: 1;
    min-width: 72px;
  }
}

.effect-box,
.stat,
.compat__tile,
.manual-unlock,
.manual-relock {
  position: relative;
  z-index: 1;
  @include pixel-clip-sm;
  image-rendering: pixelated;
  transform: translateZ(0);
  backface-visibility: hidden;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  opacity: 0.4;

  &__icon {
    font-size: 56px;
    font-family: "m6x11plus", monospace;
    color: $panel-light;
  }
  &__text {
    font-family: "m6x11plus", monospace;
    font-size: 14px;
    color: $panel-light;
    text-align: center;
    line-height: 1.8;
  }
}

.detail {
  background: $panel-darkest;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.detail__art-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 18px 16px 14px;
  flex-shrink: 0;
}

.detail__art {
  width: 58%;
  max-width: 170px;
  transform-style: preserve-3d;
}

.detail__body {
  overflow-y: auto;
  flex: 1;
  padding: 0 14px 18px;
  scrollbar-width: thin;
  scrollbar-color: $panel-mid transparent;
}

.manual-unlock {
  width: 100%;
  background: #1a4030;
  color: #22c55e;
  font-family: "m6x11plus", monospace;
  font-size: 13px;
  letter-spacing: 0.5px;
  padding: 10px 12px;
  cursor: pointer;
  transition:
    filter 0.15s,
    transform 0.1s;

  &:hover:not(:disabled) {
    filter: brightness(1.2);
  }
  &:active:not(:disabled) {
    transform: scale(0.97);
  }
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.manual-relock {
  width: 100%;
  background: #401a1a;
  color: #ef4444;
  font-family: "m6x11plus", monospace;
  font-size: 13px;
  letter-spacing: 0.5px;
  padding: 10px 12px;
  cursor: pointer;
  transition:
    filter 0.15s,
    transform 0.1s;

  &:hover:not(:disabled) {
    filter: brightness(1.25);
  }
  &:active:not(:disabled) {
    transform: scale(0.97);
  }
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.section {
  margin-bottom: 12px;

  &__head {
    background: $panel-mid;
    padding: 8px 14px;
    border-left: 4px solid $panel-light;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: "m6x11plus", monospace;
    font-size: 12px;
    color: $text-1;
    letter-spacing: 0.5px;
    font-size: 16px;
  }
  &__icon {
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 15px;
  }
  &__body {
    padding: 10px 12px;
  }
  &__body--center {
    display: flex;
    justify-content: center;
    padding: 8px 12px;
  }
  &__body--unlock {
    text-align: center;
    font-family: "m6x11plus", monospace;
    font-size: 14px;
    color: $text-2;
    line-height: 1.6;
    font-size: 16px;
  }
  /*
   * Variante para las 4 secciones de Challenge Decks (MODIFICADOR,
   * INICIO, BANEADO, BARAJA BASE). Texto desnudo, fuente legible, sin
   * mucho ornament — los textos son largos (renderizado de wikitexto)
   * y queremos que se lean cómodamente.
   */
  &__body--challenge {
    text-align: center;
    padding: 12px 14px;
    font-family: "m6x11plus", monospace;
    font-size: 13px;
    color: $text-1;
    line-height: 1.55;
    background: rgba(0, 0, 0, 0.18);
    white-space: pre-wrap;
  }
}

.effect-box {
  width: 100%;
  padding: 12px 14px;
  text-align: center;
  font-family: "m6x11plus", monospace;
  font-size: 14px;
  line-height: 1.55;
  font-weight: 700;
  background: linear-gradient(var(--tint-color), var(--tint-color)), $panel-darkest;
  white-space: pre-wrap;
}

.upgrade-box {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 6px 4px;

  &__thumb {
    width: 60px;
    aspect-ratio: 71 / 95;
    object-fit: contain;
    border-radius: 6px;
    image-rendering: pixelated;
    flex-shrink: 0;
    background: rgba(0, 0, 0, 0.25);

    &--missing {
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: "m6x11plus", monospace;
      font-size: 24px;
      color: $panel-light;
    }
  }
  &__name {
    font-family: "m6x11plus", monospace;
    font-size: 14px;
    color: $text-1;
    letter-spacing: 0.3px;
  }
}

.stats {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__row {
    display: flex;
    gap: 8px;
  }
}

.stat {
  width: 100%;
  text-align: center;
  padding: 10px 4px;
  font-family: "m6x11plus", monospace;

  &__label {
    font-size: 12px;
  }
  &__value {
    font-size: 22px;
    font-weight: 700;

    &--sm {
      font-size: 13px;
      color: $text-1;
      line-height: 1.4;
      font-weight: normal;
    }
  }
  &--buy {
    background:
      linear-gradient(rgba(192, 144, 32, 0.094), rgba(192, 144, 32, 0.094)), $panel-darkest;
    color: #c09020;
    .stat__value {
      color: #f0b030;
    }
  }
  &--sell {
    background: linear-gradient(rgba(64, 128, 32, 0.094), rgba(64, 128, 32, 0.094)), $panel-darkest;
    color: #40a030;
    .stat__value {
      color: #60c050;
    }
  }
  &--info {
    background: $panel-dark;
    padding: 10px 12px;
    text-align: left;
    .stat__label {
      color: $panel-light;
      margin-bottom: 4px;
    }
  }
}

.compat {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 4px;

  &__tile {
    width: 100%;
    padding: 10px 6px;
    text-align: center;
  }
  &__tile--copy {
    background: linear-gradient(rgba(32, 192, 80, 0.09), rgba(32, 192, 80, 0.09)), $panel-darkest;
    .compat__label {
      color: #20c050;
    }
  }
  &__tile--perish {
    background: linear-gradient(rgba(224, 128, 32, 0.09), rgba(224, 128, 32, 0.09)), $panel-darkest;
    .compat__label {
      color: #e08020;
    }
  }
  &__tile--eternal {
    background: linear-gradient(rgba(96, 128, 224, 0.09), rgba(96, 128, 224, 0.09)), $panel-darkest;
    .compat__label {
      color: #6080e0;
    }
  }
  &__symbol {
    font-size: 22px;
    line-height: 1;
  }
  &__label {
    font-family: "m6x11plus", monospace;
    font-size: 12px;
    margin-top: 6px;
  }
}

.stat__sublabel {
  font-size: 10px;
  color: #708387;
  margin-top: -4px;
  padding-bottom: 4px;
  font-family: "m6x11plus", monospace;
  opacity: 0.8;
}
</style>
