<template>
  <el-container class="app-container">
    <el-header>
      <div class="header-content">
        <h1>SEO RAG Platform</h1>
        <el-menu :default-active="activeMenu" mode="horizontal" router>
          <el-menu-item index="/upload">文档上传</el-menu-item>
          <el-menu-item index="/search">知识库搜索</el-menu-item>
          <el-menu-item index="/generate">文章生成</el-menu-item>
        </el-menu>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}

.el-header {
  background-color: #409eff;
  color: white;
  display: flex;
  align-items: center;
  padding: 0;
}

.header-content {
  width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 40px;
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
}

.el-menu {
  border: none;
  background-color: transparent;
}

.el-menu-item {
  color: white;
}

.el-menu-item:hover,
.el-menu-item.is-active {
  background-color: rgba(255, 255, 255, 0.2);
}

.el-main {
  width: 1200px;
  margin: 0 auto;
  padding: 40px 0;
}
</style>
