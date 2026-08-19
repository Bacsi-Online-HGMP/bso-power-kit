<template>
  <div class="card">
    <div class="body">Component with a pseudo-element stripe in its style block</div>
  </div>
</template>

<script setup>
const label = 'pseudo-stripe fixture';
</script>

<style scoped>
/* FLAG: same silhouette as a border side-tab, drawn as a ::before bar */
.card[data-case="Component Left Edge"]::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: #7c3aed;
}

/* PASS: neutral hairline divider */
.card[data-case="Component Neutral Divider"]::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 1px;
  background: #e5e7eb;
}
</style>
