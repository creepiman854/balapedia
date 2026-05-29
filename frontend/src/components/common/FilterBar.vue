<!--
  Barra de filtros configurable.

  modelValue: { search, rarity, status, sort, type }
  enabled:    array de filtros visibles (los demás se ocultan).
  typeOptions: array de { value, label } cuando 'type' está habilitado.
              Cada vista pasa sus propias opciones (pack types, modifier
              kinds, etc.) — la barra es agnóstica al dominio.

  Por defecto se muestran search + rarity + status + sort. La opción
  'type' SOLO se renderiza si la vista la incluye en enabled Y pasa
  typeOptions; si no, el select no aparece y el filtro se ignora.
-->
<template>
  <div class="filterbar">
    <span class="filterbar__title">FILTERS</span>

    <div v-if="show('search')" class="filterbar__search">
      <span class="filterbar__icon"> <iconify-icon icon="pixel:search" noobserver /></span>
      <input
        type="text"
        :placeholder="searchPlaceholder"
        :value="modelValue.search"
        @input="update('search', $event.target.value)"
      />
      <button
        v-if="modelValue.search"
        type="button"
        class="filterbar__clear"
        aria-label="Clear search"
        @click="update('search', '')"
      >
        ✕
      </button>
    </div>

    <select
      v-if="show('rarity')"
      class="filterbar__select"
      :value="modelValue.rarity"
      @change="update('rarity', $event.target.value)"
    >
      <option value="all">Rarity: All</option>
      <option value="common">Common</option>
      <option value="uncommon">Uncommon</option>
      <option value="rare">Rare</option>
      <option value="legendary">Legendary</option>
    </select>

    <select
      v-if="show('type') && typeOptions.length"
      class="filterbar__select"
      :value="modelValue.type"
      @change="update('type', $event.target.value)"
    >
      <option v-for="opt in typeOptions" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>

    <select
      v-if="show('size') && sizeOptions.length"
      class="filterbar__select"
      :value="modelValue.size"
      @change="update('size', $event.target.value)"
    >
      <option v-for="opt in sizeOptions" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>

    <select
      v-if="show('sort')"
      class="filterbar__select"
      :value="modelValue.sort"
      @change="update('sort', $event.target.value)"
    >
      <option value="id">Sort: #</option>
      <option value="name">A-Z</option>
      <option v-if="show('rarity')" value="rarity">Rarity</option>
    </select>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Object, required: true },
  /**
   * Filtros visibles.
   *   - 'search'  → input de búsqueda libre
   *   - 'rarity'  → solo aplica a jokers (lista hardcoded)
   *   - 'status'  → unlocked/locked
   *   - 'type'    → select dinámico con typeOptions
   *   - 'sort'    → orden ascendente
   */
  enabled: {
    type: Array,
    default: () => ["search", "rarity", "status", "sort"],
  },
  /**
   * Opciones del select 'type' (formato: [{ value, label }, ...]).
   * Se ignora si 'type' no está en enabled.
   */
  typeOptions: {
    type: Array,
    default: () => [],
  },
  sizeOptions: {
    type: Array,
    default: () => [],
  },
  searchPlaceholder: { type: String, default: "Search..." },
});

const emit = defineEmits(["update:modelValue"]);

function show(key) {
  return props.enabled.includes(key);
}

function update(field, value) {
  emit("update:modelValue", { ...props.modelValue, [field]: value });
}
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.filterbar {
  background: $panel-mid;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  box-shadow: 0 4px 16px $shadow;
  /*
   * NO usamos `flex: 1` aquí: si esto está dentro de un flex-column
   * (como ocurre en JokersView), `flex: 1` lo estiraría verticalmente
   * a toda la altura disponible. Cuando el FilterBar vive dentro de
   * .toolbar (consumables/colección), el propio .toolbar aplica
   * `:deep(.filterbar) { flex: 1 }` para que crezca a lo ancho.
   */
  @include pixel-clip;

  &__title {
    font-family: "m6x11plus", monospace;
    font-size: 13px;
    color: $text-3;
    margin-right: 4px;
    letter-spacing: 0.5px;
  }

  &__search {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 160px;
    background: $panel-dark;
    color: $text-1;
    padding: 8px 12px;
    gap: 6px;
    @include pixel-clip-sm;

    input {
      background: transparent;
      border: none;
      color: $text-1;
      font-family: "m6x11plus", monospace;
      font-size: 18px;
      outline: none;
      width: 100%;
      flex: 1;
      min-width: 0;
    }
  }

  &__clear {
    flex-shrink: 0;
    background: transparent;
    border: none;
    color: $text-3;
    font-family: "m6x11plus", monospace;
    font-size: 14px;
    cursor: pointer;
    padding: 2px 6px;
    transition:
      color 0.12s,
      transform 0.12s;

    &:hover {
      color: $text-1;
      transform: scale(1.15);
    }
    &:active {
      transform: scale(0.92);
    }
  }

  &__icon {
    color: $panel-light;
    font-size: 16px;
    display: flex;
    align-items: center;
  }

  &__select {
    appearance: none;
    -webkit-appearance: none;
    background: $panel-dark;
    border: none;
    color: $text-1;
    font-family: "m6x11plus", monospace;
    font-size: 18px;
    padding: 8px 28px 8px 12px;
    outline: none;
    cursor: pointer;
    min-width: 110px;
    background-image: none;
    @include pixel-clip-sm;
  }
}
</style>
