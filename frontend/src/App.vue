<template>
  <router-view />
</template>

<script setup>
// 使用 Vue Router 来管理页面
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Inter', 'Space Grotesk', 'Noto Sans SC', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #142019;
  background-color: #f0f4ec;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #dfe8df;
}

::-webkit-scrollbar-thumb {
  background: #183124;
}

::-webkit-scrollbar-thumb:hover {
  background: #d5f26b;
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}
</style>
