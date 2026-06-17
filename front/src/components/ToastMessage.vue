<template>
  <div v-if="toast.message" :class="['toast', toast.type]" role="status">
    {{ toast.message }}
  </div>
</template>

<script setup>
defineProps({
  toast: { type: Object, required: true },
})
</script>
