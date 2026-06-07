<template>
  <div class="search-page">
    <el-card class="search-card" shadow="never">
      <el-form :model="form" label-width="120px">
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
        <p class="scope-note">
          检索范围：系统级共享库 + 当前租户「{{ props.tenantId }}」，不会返回其他租户的文档。
        </p>
        <el-divider />
        <div v-for="(result, index) in results" :key="index" class="result-item">
          <el-card shadow="hover">
            <div class="result-meta">
              <div class="tags">
                <el-tag :type="result.source === 'milvus' ? 'primary' : 'success'">
                  {{ result.source }}
                </el-tag>
                <el-tag
                  :type="scopeOf(result) === 'system' ? 'warning' : 'info'"
                  effect="plain"
                >
                  {{ scopeOf(result) === 'system' ? '系统级' : '租户级' }}
                </el-tag>
              </div>
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

const props = defineProps({
  tenantId: { type: String, default: 'tenant_001' },
  collectionName: { type: String, default: 'acme_kb' }
})

const form = ref({ query: '' })

const loading = ref(false)
const results = ref([])

const scopeOf = (result) => result?.metadata?.access_scope || result?.metadata?.scope || 'tenant'

const handleSearch = async () => {
  if (!form.value.query) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  
  loading.value = true
  try {
    const params = {
      query: form.value.query,
      tenantId: props.tenantId,
      collectionName: props.collectionName
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
  max-width: 100%;
  margin: 0;
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

.tags {
  display: flex;
  gap: 8px;
}

.scope-note {
  color: #909399;
  font-size: 13px;
  margin: 4px 0 0;
}

.score {
  color: #909399;
  font-size: 14px;
}
</style>
