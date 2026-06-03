<template>
  <div class="search-page">
    <el-card class="search-card">
      <template #header>
        <div class="card-header">
          <span>知识库搜索</span>
        </div>
      </template>
      
      <el-form :model="form" label-width="120px">
        <el-form-item label="租户ID">
          <el-input v-model="form.tenantId" placeholder="请输入租户ID" />
        </el-form-item>
        <el-form-item label="集合名称">
          <el-input v-model="form.collectionName" placeholder="请输入集合名称" />
        </el-form-item>
        <el-form-item label="搜索内容">
          <el-input v-model="form.query" placeholder="请输入搜索内容" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch" :loading="loading">
            搜索
          </el-button>
        </el-form-item>
      </el-form>
      
      <div v-if="results.length > 0" class="search-results">
        <h3>搜索结果 (Top {{ results.length }})</h3>
        <el-divider />
        <div v-for="(result, index) in results" :key="index" class="result-item">
          <el-card shadow="hover">
            <div class="result-meta">
              <el-tag :type="result.source === 'milvus' ? 'primary' : 'success'">
                {{ result.source }}
              </el-tag>
              <span class="score">Score: {{ result.rerank_score?.toFixed(4) || result.score?.toFixed(4) }}</span>
            </div>
            <p>{{ result.text }}</p>
          </el-card>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const form = ref({
  tenantId: 'default',
  collectionName: 'default',
  query: ''
})

const loading = ref(false)
const results = ref([])

const handleSearch = async () => {
  if (!form.value.query) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  
  loading.value = true
  try {
    const params = {
      query: form.value.query,
      tenantId: form.value.tenantId,
      collectionName: form.value.collectionName
    }
    const response = await axios.post('/api/v1/search', null, { params })
    results.value = response.data.results
    if (results.value.length === 0) {
      ElMessage.info('未找到相关内容')
    }
  } catch (error) {
    ElMessage.error('搜索失败: ' + error.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.search-page {
  max-width: 900px;
  margin: 0 auto;
}

.search-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.search-results {
  margin-top: 30px;
}

.result-item {
  margin-bottom: 20px;
}

.result-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  align-items: center;
}

.score {
  color: #909399;
  font-size: 14px;
}
</style>
