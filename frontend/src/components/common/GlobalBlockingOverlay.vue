<template>
  <div class="blocking-overlay">
    <div class="blocking-overlay__box">
      PROCESSING...
      <br />
      PLEASE WAIT
    </div>
  </div>
</template>

<style scoped lang="scss">
@use "@/assets/styles/mixins" as *;

.blocking-overlay {
  position: fixed;

  top: var(--app-header-height);
  left: 0;
  right: 0;
  bottom: 0;

  z-index: 9000;

  display: flex;
  align-items: center;
  justify-content: center;

  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(3px);
}

.blocking-overlay__box {
  padding: 18px 24px;

  background: rgba(20, 24, 28, 0.96);

  color: #fff;

  font-family: "m6x11plus", monospace;
  font-size: 18px;
  line-height: 1.4;
  text-align: center;
  letter-spacing: 1px;

  @include pixel-clip;
}
</style>
