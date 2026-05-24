<!--
  Barra de filtros configurable.

  modelValue: { search, rarity, status, sort }
  enabled:    array de filtros visibles (los demás se ocultan).

  Por defecto se muestran todos. Para consumibles, el padre pasa
  enabled=['search','sort'] (no hay rareza ni estado unlocked/locked
  por ahora).
-->
<template>
  <div class="filterbar">
    <span class="filterbar__title">FILTROS</span>

    <div v-if="show('search')" class="filterbar__search">
      <span class="filterbar__icon">🔍</span>
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
        aria-label="Limpiar búsqueda"
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
      <option value="all">Rareza: Todas</option>
      <option value="common">Común</option>
      <option value="uncommon">Inusual</option>
      <option value="rare">Raro</option>
      <option value="legendary">Legendario</option>
    </select>

    <select
      v-if="show('status')"
      class="filterbar__select"
      :value="modelValue.status"
      @change="update('status', $event.target.value)"
    >
      <option value="all">Estado: Todos</option>
      <option value="unlocked">Desbloqueados</option>
      <option value="locked">Bloqueados</option>
    </select>

    <select
      v-if="show('sort')"
      class="filterbar__select"
      :value="modelValue.sort"
      @change="update('sort', $event.target.value)"
    >
      <option value="id">Orden: #</option>
      <option value="name">Orden: A-Z</option>
      <option v-if="show('rarity')" value="rarity">Orden: Rareza</option>
    </select>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Object, required: true },
  /**
   * Filtros visibles. Por defecto todos.
   *   - 'search'  → input de búsqueda libre
   *   - 'rarity'  → solo aplica a jokers
   *   - 'status'  → unlocked/locked, requiere overlay del backend
   *   - 'sort'    → orden ascendente
   */
  enabled: {
    type: Array,
    default: () => ['search', 'rarity', 'status', 'sort'],
  },
  searchPlaceholder: { type: String, default: 'Buscar...' },
})

const emit = defineEmits(['update:modelValue'])

function show(key) {
  return props.enabled.includes(key)
}

function update(field, value) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.filterbar {
  background: $panel-mid;
  padding: 10px 14px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  box-shadow: 0 4px 16px $shadow;
  @include pixel-clip;

  &__title {
    font-family: 'm6x11plus', monospace;
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
      font-family: 'm6x11plus', monospace;
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
    font-family: 'm6x11plus', monospace;
    font-size: 14px;
    cursor: pointer;
    padding: 2px 6px;
    transition: color 0.12s, transform 0.12s;

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
  }

  &__select {
    appearance: none;
    -webkit-appearance: none;
    background: $panel-dark;
    border: none;
    color: $text-1;
    font-family: 'm6x11plus', monospace;
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
