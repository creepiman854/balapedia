<template>
  <div class="not-found-view">
    <div class="not-found-panel">
      <h1>404</h1>

      <h2>PAGE NOT FOUND</h2>

      <p>
        The page you are looking for does not exist or has been moved.
      </p>

      <RouterLink to="/jokers" class="back-btn">
        RETURN TO BALAPEDIA
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.not-found-view {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 0;
  padding: 24px;
}

.not-found-panel {
  width: 100%;
  max-width: 520px;
  padding: 32px;
  text-align: center;
  background: rgba(26, 42, 46, 0.85);
  box-shadow: 0 8px 32px $shadow;
  @include pixel-clip;

  h1 {
    margin: 0;
    font-family: "m6x11plus", monospace;
    font-size: 72px;
    color: $text-1;
    line-height: 1;
  }

  h2 {
    margin: 12px 0 20px;
    font-family: "m6x11plus", monospace;
    font-size: 24px;
    letter-spacing: 1px;
    color: $text-1;
  }

  p {
    margin: 0 0 24px;
    font-family: "m6x11plus", monospace;
    font-size: 14px;
    color: $text-2;
    line-height: 1.5;
  }
}

.back-btn {
  display: inline-block;
  padding: 10px 18px;
  text-decoration: none;
  font-family: "m6x11plus", monospace;
  font-size: 14px;
  color: $text-1;
  background: $panel-mid;
  transition: filter 0.15s;

  @include pixel-clip-sm;

  @include can-hover {
    &:hover {
      filter: brightness(1.15);
    }
  }
}

@include mobile {
  .not-found-panel {
    padding: 24px;

    h1 {
      font-size: 56px;
    }

    h2 {
      font-size: 20px;
    }
  }
}
</style>
