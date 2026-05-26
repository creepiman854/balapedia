<!--
  Vista de Logros.

  Distinta al resto: los logros tienen un único campo de información
  (name + description + icon_url), así que NO existe ItemDetailPanel.
  El layout es una columna de "filas" (estilo lista) en lugar del grid
  de cartas que usan jokers/consumibles/colección.

  Comportamiento clave:
    · ProgressBar SOLO se muestra con sesión iniciada (sin auth todos
      saldrían como "desbloqueados", así que no aporta información).
    · FilterBar con search + status. ESTADO también se oculta sin auth
      por el mismo motivo (todos visibles → filtro inútil).
    · Cada fila:
        - icono (icon_url, con drop-shadow + brillo si desbloqueado)
        - nombre + descripción (NUNCA "???" / "Logro oculto" — el usuario
          tiene que poder leer cómo desbloquearlo aunque esté locked)
        - botón MARCAR COMO DESBLOQUEADO solo si:
            authenticated && !user.steam_id && locked
          Las cuentas Steam sincronizan automáticamente desde la API,
          así que el botón manual no aplica para ellas.
        - punto de estado a la derecha: verde con brillo si desbloqueado,
          oscuro si no.
    · Los logros bloqueados se ven con opacity 0.5 + saturación reducida
      del icono — efecto visual claro pero sin esconder texto.

  Mejoras extra incluidas (sutiles, sin alterar el diseño base):
    · Hover sobre fila → ligero highlight de fondo + leve translate.
    · El punto verde de desbloqueado palpita (pulse) muy sutilmente.
    · Pequeña animación scale-in al cargar la lista (escalonada).
-->
<template>
  <div class="achievements-view">
    <!--
      Barra de progreso global. Solo con auth — el cálculo se hace sobre
      la lista COMPLETA (no `filtered`) para que el % refleje el progreso
      real, no el filtrado actual.
    -->
    <ProgressBar
      v-if="isAuthenticated && achievements.length"
      :value="totalUnlocked"
      :max="achievements.length"
      color="#ef4444"
      label="LOGROS DESBLOQUEADOS"
    />

    <FilterBar v-model="filters" :enabled="enabledFilters" search-placeholder="Buscar logro..." />

    <div class="count">
      <template v-if="loading">Cargando logros...</template>
      <template v-else-if="error">{{ error }}</template>
      <template v-else>{{ filtered.length }} logros encontrados</template>
    </div>

    <div class="list-scroll">
      <ul v-if="!loading && !error" class="list">
        <li
          v-for="(ach, idx) in filtered"
          :key="ach.id"
          class="row"
          :class="{ 'row--locked': isLocked(ach) }"
          :style="{ animationDelay: `${Math.min(idx, 12) * 30}ms` }"
        >
          <!-- Icono — siempre icon_url, no emojis. -->
          <div class="row__icon">
            <img
              v-if="ach.icon_url"
              :src="ach.icon_url"
              :alt="ach.name"
              class="row__icon-img"
              draggable="false"
              loading="lazy"
            />
            <div v-else class="row__icon-fallback">?</div>
          </div>

          <div class="row__body">
            <div class="row__name">{{ ach.name }}</div>
            <div class="row__desc">{{ ach.description }}</div>
          </div>

          <!--
            Botón manual: solo con sesión, sin steam_id, y solo si está
            locked. Las cuentas Steam no lo ven nunca.
          -->
          <button
            v-if="canShowManualUnlock(ach)"
            type="button"
            class="row__unlock"
            @click.stop="onManualUnlock(ach)"
          >
            MARCAR COMO DESBLOQUEADO
          </button>

          <span class="row__dot" :class="{ 'row__dot--on': !isLocked(ach) }" />
        </li>
      </ul>

      <div v-if="!loading && !error && filtered.length === 0" class="empty">
        Sin logros con esos filtros.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useBackgroundStore } from "@/stores/background";
import { fetchAllAchievements, unlockAchievement } from "@/services/achievements";

import ProgressBar from "@/components/common/ProgressBar.vue";
import FilterBar from "@/components/common/FilterBar.vue";

const authStore = useAuthStore();
const { isAuthenticated, user, lastSyncedAt } = storeToRefs(authStore);
const bgStore = useBackgroundStore();

// ── Datos ────────────────────────────────────────────────────────────
const achievements = ref([]);
const loading = ref(false);
const error = ref("");

async function loadAchievements() {
  loading.value = true;
  error.value = "";
  try {
    achievements.value = await fetchAllAchievements({
      authenticated: isAuthenticated.value,
    });
  } catch (e) {
    console.error("[AchievementsView] no se pudieron cargar", e);
    error.value = "No se pudieron cargar los logros. ¿Backend caído?";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  bgStore.setPreset("achievements");
  loadAchievements();
});
// Si el usuario inicia o cierra sesión, recargamos para que el overlay
// `unlocked_for_me` aparezca o desaparezca del payload del backend.
watch(isAuthenticated, loadAchievements);
watch(lastSyncedAt, loadAchievements);

// ── Filtros ──────────────────────────────────────────────────────────
const filters = ref({
  search: "",
  status: "all",
});

/**
 * Solo activamos search y status. ESTADO desaparece sin auth (sin
 * sesión todos los logros se ven como desbloqueados, así que filtrar
 * por estado no aporta nada).
 */
const enabledFilters = computed(() => {
  const base = ["search", "status"];
  return isAuthenticated.value ? base : base.filter((f) => f !== "status");
});

/**
 * Sin auth, todos visibles (no hay bloqueado).
 * Con auth, usamos `unlocked_for_me` del overlay del backend.
 *
 * No usamos `isItemLocked` de constants/items porque los logros no son
 * Unlockable y no tienen `unlock_condition` / `unlock_factor` — la
 * lógica aquí es más simple.
 */
function isLocked(ach) {
  if (!isAuthenticated.value) return false;
  return !ach.unlocked_for_me;
}

const filtered = computed(() => {
  const search = filters.value.search.toLowerCase();
  return achievements.value.filter((ach) => {
    if (filters.value.status === "unlocked" && isLocked(ach)) return false;
    if (filters.value.status === "locked" && !isLocked(ach)) return false;
    if (
      search &&
      !(ach.name || "").toLowerCase().includes(search) &&
      !(ach.description || "").toLowerCase().includes(search)
    )
      return false;
    return true;
  });
});

const totalUnlocked = computed(() => achievements.value.filter((a) => !isLocked(a)).length);

// ── Manual unlock ────────────────────────────────────────────────────
/**
 * Botón manual solo aparece para usuarios SIN steam_id. Las cuentas
 * Steam tienen sincronización automática desde la API oficial, así que
 * un botón "marcar como desbloqueado" sería contradictorio (y podría
 * crear conflicto con el próximo sync).
 */
function canShowManualUnlock(ach) {
  if (!isAuthenticated.value) return false;
  if (user.value?.steam_id) return false;
  return isLocked(ach);
}

async function onManualUnlock(ach) {
  if (!ach) return;
  try {
    await unlockAchievement(ach.id);
    // Mutamos la fila localmente para no tener que re-fetchear toda la
    // lista — más fluido visualmente, el dot pasa a verde al instante.
    const target = achievements.value.find((a) => a.id === ach.id);
    if (target) {
      target.unlocked_for_me = true;
      target.unlocked_at = new Date().toISOString();
    }
  } catch (e) {
    console.error("[AchievementsView] manual unlock falló", e);
    // 401 = sesión caducada. Abrimos el AuthModal — es la acción que
    // el usuario necesita; un alert técnico no le ayuda a recuperarse.
    if (e?.response?.status === 401) {
      authStore.openAuthModal();
      return;
    }
    alert("No se pudo marcar como desbloqueado. " + (e.message || ""));
  }
}
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.achievements-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 12px;
}

/*
 * Texto sobre el shader: mismo tratamiento que en JokersView y
 * ConsumiblesView — text-shadow ligera (0 3px 0 #00000070) para
 * contraste sin pesar visualmente.
 */
.view-title {
  font-family: "m6x11plus", monospace;
  font-size: 22px;
  color: #ffffff;
  text-shadow: 0 3px 0 #00000070;
  letter-spacing: 1px;
  padding-left: 4px;
}

.count {
  font-family: "m6x11plus", monospace;
  font-size: 16px;
  color: #ffffff;
  text-shadow: 0 3px 0 #00000070;
  padding-left: 4px;
  letter-spacing: 0.4px;
}

/*
 * Contenedor scroll de la lista — panel translúcido del shader detrás,
 * idéntico patrón al grid-scroll de las otras vistas para consistencia.
 */
.list-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  background: rgba(26, 42, 46, 0.6); // = $panel-darkest con alpha
  scrollbar-width: thin;
  scrollbar-color: $panel-mid transparent;
  @include pixel-clip;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/*
 * Fila de logro — pixel-clipped igual que el resto de paneles.
 * Animación de entrada: scale-in muy sutil escalonada por index para
 * que al cargar la lista se sienta viva pero no exagerada.
 *
 * Tamaños bumpeados (pase 2):
 *   - padding 16/20 (era 12/16)
 *   - gap 18 (era 14)
 *   El icono y los textos crecen en sus propias reglas, así la fila
 *   queda más alta y la imagen / nombre / descripción se leen mejor.
 */
.row {
  --target-opacity: 1;

  display: flex;
  align-items: center;
  gap: 18px;
  padding: 16px 20px;
  background: $panel-mid;
  box-shadow: 0 3px 8px $shadow;
  opacity: var(--target-opacity);
  transition:
    background 0.18s ease,
    transform 0.18s ease,
    opacity 0.2s ease;
  @include pixel-clip;
  animation: rowIn 0.32s ease backwards;

  &:hover {
    background: $panel-medlight;
    transform: translateY(-1px);
  }

  &--locked {
    --target-opacity: 0.5;

    .row__icon-img {
      filter: grayscale(0.65) brightness(0.85);
    }

    // Hover sobre el contenedor general (logro bloqueado)
    &:hover {
      --target-opacity: 0.75;
      background: $panel-mid;
      transform: none;
    }

    // Si estamos haciendo hover sobre el botón DENTRO de esta fila,
    // sube la opacidad de TODA LA FILA al 100%.
    &:has(.row__unlock:hover) {
      --target-opacity: 1;
    }
  }
}

@keyframes rowIn {
  0% {
    opacity: 0;
    transform: translateY(10px);
  }
}

.row__icon {
  width: 64px;
  height: 64px;
  flex-shrink: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  @include pixel-clip-sm;
}

.row__icon-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.5));
}

.row__icon-fallback {
  font-family: "m6x11plus", monospace;
  font-size: 30px;
  color: $panel-light;
}

.row__body {
  flex: 1;
  min-width: 0;
}

.row__name {
  font-family: "m6x11plus", monospace;
  font-size: 17px;
  color: $text-1;
  letter-spacing: 0.4px;
  margin-bottom: 6px;
  // Truncar a una línea para que filas con nombres largos no rompan
  // el layout en grids estrechos.
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.row__desc {
  font-family: "m6x11plus", monospace;
  font-size: 18px;
  color: $text-2;
  line-height: 1.45;
}

/*
 * Botón "MARCAR COMO DESBLOQUEADO". Mismo estilo aproximado que el
 * de ItemDetailPanel para coherencia. Se oculta automáticamente para
 * cuentas con steam_id.
 */
.row__unlock {
  flex-shrink: 0;
  background: $panel-dark;
  border: 1px solid $panel-medlight;
  color: $text-1;
  font-family: "m6x11plus", monospace;
  font-size: 12px;
  letter-spacing: 0.5px;
  padding: 10px 14px;
  cursor: pointer;

  // Añadimos opacidad inicial y transición al botón en sí
  opacity: 0.7;
  transition:
    background 0.15s,
    transform 0.1s,
    opacity 0.15s;
  @include pixel-clip-sm;

  &:hover {
    background: $panel-medlight;
    opacity: 1; // El botón brilla al 100% (y gracias al :has, la fila también)
  }

  &:active {
    transform: scale(0.96);
  }
}

/*
 * Punto de estado:
 *  - bloqueado: gris muy oscuro, sin glow.
 *  - desbloqueado: verde sólido con halo + pulso suave para que sea
 *    fácil de localizar visualmente al hacer scroll.
 */
.row__dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: $panel-darkest;
  flex-shrink: 0;
  transition:
    background 0.2s,
    box-shadow 0.2s;

  &--on {
    background: #22c55e;
    box-shadow: 0 0 8px #22c55e;
    animation: pulseGreen 2.4s ease-in-out infinite;
  }
}

@keyframes pulseGreen {
  0%,
  100% {
    box-shadow: 0 0 8px #22c55e;
  }
  50% {
    box-shadow: 0 0 14px #22c55e;
  }
}

.empty {
  color: $text-3;
  font-family: "m6x11plus", monospace;
  font-size: 14px;
  text-align: center;
  padding: 24px 0;
}
</style>
