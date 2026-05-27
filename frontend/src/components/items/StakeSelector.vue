<!--
  Selector de progresión de stakes/stickers.

  Muestra 8 thumbnails (stickers para jokers, stakes para decks)
  en una columna vertical. La miniatura del stake activo
  (highest_stake_order) se resalta con borde y glow. Click sobre una
  miniatura superior promociona el sticker.

  Emite:
    @set-stake(stakeOrder) — cuando el usuario clickea un stake
    diferente (solo si no tiene steam_id). El padre hace el POST.

  Read-only para cuentas Steam (solo muestra el estado actual).
-->
<template>
  <div v-if="items.length" class="stake-sel">
    <div class="stake-sel__label">PROGRESO</div>
    <div class="stake-sel__grid">
      <div
        v-for="entry in items"
        :key="entry.order"
        class="stake-sel__item"
        :class="{
          'stake-sel__item--active': entry.order <= currentOrder,
          'stake-sel__item--gold': entry.order === 8 && entry.order <= currentOrder,
          'stake-sel__item--clickable': canInteract && entry.order > currentOrder,
        }"
        :title="entry.name + (entry.description ? ': ' + entry.description : '')"
        @click="onClickStake(entry.order, $event)"
        @click.stop="onClickStake(entry.order)"
      >
        <img
          v-if="entry.image_url"
          :src="entry.image_url"
          :alt="entry.name"
          class="stake-sel__img"
          :class="{ 'stake-sel__img--sticker': itemType === 'JOKER' }"
          draggable="false"
        />
        <div v-else class="stake-sel__img stake-sel__img--fallback">
          {{ entry.order }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useProgressionStore } from "@/stores/progression";

const props = defineProps({
  /** El item seleccionado (joker o deck, con type y highest_stake_order). */
  item: { type: Object, default: null },
});

const emit = defineEmits(["set-stake"]);

const authStore = useAuthStore();
const { user } = storeToRefs(authStore);
const progStore = useProgressionStore();

onMounted(() => progStore.init());

/** Usuarios autenticados siempre pueden promocionar manualmente. */
const canInteract = computed(() => true);

const currentOrder = computed(() => props.item?.highest_stake_order || 0);

const itemType = computed(() => {
  const t = String(props.item?.type || "").toUpperCase();
  return t === "JOKER" || t === "DECK" ? t : null;
});

/**
 * Lista de 8 entradas ordenadas por stake_order, con la imagen
 * apropiada según el tipo de item (sticker para joker, stake para deck).
 */
const items = computed(() => {
  if (!itemType.value || !progStore.loaded) return [];

  if (itemType.value === "JOKER") {
    return progStore.progressionStickers.map((s) => ({
      order: s.stake?.stake_order ?? 0,
      image_url: s.image_url,
      name: s.name,
      description: s.description || "",
    }));
  }

  // DECK
  return progStore.sortedStakes.map((s) => ({
    order: s.stake_order,
    image_url: s.image_url,
    name: s.name,
    description: s.effect_description || "",
  }));
});

function onClickStake(order) {
  if (!canInteract.value) return;

  // Toggle off: si clicka el que ya tiene, lo bajamos a 0
  const newOrder = order === currentOrder.value ? 0 : order;

  emit("set-stake", newOrder);
}
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.stake-sel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 100%;

  &__label {
    font-family: "m6x11plus", monospace;
    font-size: 10px;
    color: $text-3;
    letter-spacing: 0.5px;
  }

  &__grid {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: center;
    gap: 6px;
    background: rgba(0, 0, 0, 0.35);
    padding: 3px;
    @include pixel-clip-sm;
  }

  &__item {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.35;
    overflow: visible;
    transition:
      opacity 0.15s,
      transform 0.1s;
    cursor: pointer;

    &--active {
      opacity: 1;
    }

    /* El efecto Gold lo aplicamos a la imagen mediante filtro en lugar de sombra de caja */
    &--gold {
      filter: drop-shadow(0 0 6px #f0a020);
    }

    &:hover {
      opacity: 1;
      transform: scale(1.15);
    }
  }

  &__img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    image-rendering: pixelated;
    pointer-events: none;

    /* Zoom específico para stickers de Jokers */
    &--sticker {
      object-fit: cover;
      object-position: top right;
      transform-origin: top right;
      transform: scale(3) translate(1.7px, -1.7px);
    }

    &--fallback {
      font-family: "m6x11plus", monospace;
      font-size: 14px;
      color: $text-3;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}
</style>
