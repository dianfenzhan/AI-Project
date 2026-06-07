<template>
  <el-container class="app-container">
    <el-header>
      <div class="header-content">
        <h1>SEO RAG Platform</h1>
        <span class="header-subtitle">租户文档 · 系统文档 · 知识库搜索 · 文章生成</span>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #f5f7fa;
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
  align-items: baseline;
  gap: 16px;
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
}

.header-subtitle {
  font-size: 14px;
  opacity: 0.9;
}

.el-main {
  width: 1200px;
  margin: 0 auto;
  padding: 32px 0 48px;
}
</style>
