<template>
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <!-- Left hemisphere outline -->
    <path d="M11 4C8.5 4 7 5.5 7 7.5C5 7.8 4 9.2 4 11C4 12 4.4 12.8 5 13.3C4.4 13.9 4 14.8 4 15.8C4 17.5 5.3 18.9 7 19.2C7.3 20.2 8.3 21 9.5 21C10.3 21 11 20.6 11 20.6V4Z"
          stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
    <!-- Right hemisphere outline -->
    <path d="M13 4C15.5 4 17 5.5 17 7.5C19 7.8 20 9.2 20 11C20 12 19.6 12.8 19 13.3C19.6 13.9 20 14.8 20 15.8C20 17.5 18.7 18.9 17 19.2C16.7 20.2 15.7 21 14.5 21C13.7 21 13 20.6 13 20.6V4Z"
          stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
    <!-- Neural connections (circuit-like nodes) -->
    <circle cx="9" cy="9" r="0.8" fill="currentColor" />
    <circle cx="15" cy="9" r="0.8" fill="currentColor" />
    <circle cx="9" cy="14" r="0.8" fill="currentColor" />
    <circle cx="15" cy="14" r="0.8" fill="currentColor" />
    <circle cx="12" cy="11.5" r="0.8" fill="currentColor" />
    <!-- Synaptic lines -->
    <line x1="9" y1="9" x2="12" y2="11.5" stroke="currentColor" stroke-width="0.7" opacity="0.6" />
    <line x1="15" y1="9" x2="12" y2="11.5" stroke="currentColor" stroke-width="0.7" opacity="0.6" />
    <line x1="9" y1="14" x2="12" y2="11.5" stroke="currentColor" stroke-width="0.7" opacity="0.6" />
    <line x1="15" y1="14" x2="12" y2="11.5" stroke="currentColor" stroke-width="0.7" opacity="0.6" />
  </svg>
</template>

<script setup>
</script>
