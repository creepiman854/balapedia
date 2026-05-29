import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useDictionaryStore = defineStore('dictionary', () => {
  const itemMap = ref(new Map());
  const itemNamesPattern = ref('');

  // Lista negra de palabras demasiado genéricas para autoscaneo
  const BLACKLIST = ["joker"];

  function registerItems(items) {
    if (!items || !items.length) return;

    let changed = false;
    for (const item of items) {
      if (item && item.name && item.image_url) {
        const nameClean = item.name.trim();
        const lowerName = nameClean.toLowerCase();

        if (lowerName.length > 2 && !itemMap.value.has(lowerName)) {
          itemMap.value.set(lowerName, item.image_url);
          changed = true;
        }

        // Registramos automáticamente la versión negativa si existe
        if (item.negative_image_url) {
          const negName = "negative " + lowerName;
          if (!itemMap.value.has(negName)) {
            itemMap.value.set(negName, item.negative_image_url);
            changed = true;
          }
        }
      }
    }

    if (changed) {
      // Reconstruimos el patrón.
      // IMPORTANTE: Aquí aplicamos la Blacklist. Así, "joker" existe en el mapa
      // pero no se escanea globalmente de forma automática.
      const names = Array.from(itemMap.value.keys())
        .filter(name => !BLACKLIST.includes(name))
        .map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
        .sort((a, b) => b.length - a.length);

      if (names.length > 0) {
        itemNamesPattern.value = names.join('|');
      }
    }
  }

  function getImage(name) {
    if (!name) return null;
    const lowerName = name.trim().toLowerCase();

    if (itemMap.value.has(lowerName)) {
      return itemMap.value.get(lowerName);
    }

    if (lowerName.endsWith('s') && itemMap.value.has(lowerName.slice(0, -1))) {
      return itemMap.value.get(lowerName.slice(0, -1));
    }

    return null;
  }

  return { itemMap, itemNamesPattern, registerItems, getImage };
});
