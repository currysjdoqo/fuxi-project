<template>
  <div id="app">
    <nav class="app-nav">
      <router-link to="/">练习</router-link>
      <router-link to="/import">导入</router-link>
      <router-link to="/wrong">错题本</router-link>
      <router-link to="/important">重点题</router-link>
      <router-link to="/trash">垃圾桶</router-link>
      <router-link to="/review">复习</router-link>
      <router-link to="/settings">设置</router-link>
    </nav>
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
}

.app-nav {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  gap: 8px;
  padding: 10px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.app-nav a {
  color: #606266;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.app-nav a.router-link-active {
  color: #fff;
  background: #409eff;
}
</style>
