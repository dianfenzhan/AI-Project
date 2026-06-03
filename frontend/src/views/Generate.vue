<template>
  <div class="generate-page">
    <el-card class="generate-card">
      <template #header>
        <div class="card-header">
          <span>SEO 文章生成</span>
        </div>
      </template>
      
      <el-form :model="form" label-width="120px">
        <el-form-item label="租户ID">
          <el-input v-model="form.tenantId" placeholder="请输入租户ID" />
        </el-form-item>
        <el-form-item label="集合名称">
          <el-input v-model="form.collectionName" placeholder="请输入集合名称" />
        </el-form-item>
        <el-form-item label="AI 模型">
          <el-select v-model="form.llmProvider" placeholder="请选择AI模型">
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="通义千问" value="qianwen" />
            <el-option label="豆包" value="doubao" />
          </el-select>
        </el-form-item>
        <el-form-item label="主题">
          <el-input v-model="form.topic" placeholder="请输入文章主题" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="form.keywords" placeholder="请输入关键词，用逗号分隔" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleGenerateTitles" :loading="loadingTitles">
            第一步：生成标题
          </el-button>
          <el-button
            type="success"
            @click="handleGenerateOutlines"
            :disabled="!threadId || !selectedTitle"
            :loading="loadingOutlines"
            style="margin-left: 12px"
          >
            第二步：生成大纲
          </el-button>
          <el-button
            type="warning"
            @click="handleGenerateArticle"
            :disabled="!threadId || !selectedOutline"
            :loading="loadingArticle"
            style="margin-left: 12px"
          >
            第三步：生成文章
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 标题选择 -->
      <div v-if="titles.length > 0" class="section">
        <h3>选择标题（5选1）</h3>
        <el-radio-group v-model="selectedTitle">
          <el-radio v-for="(title, index) in titles" :key="index" :label="title">
            {{ title }}
          </el-radio>
        </el-radio-group>
      </div>
      
      <!-- 大纲选择 -->
      <div v-if="outlines.length > 0" class="section">
        <h3>选择大纲（3选1）</h3>
        <el-radio-group v-model="selectedOutline">
          <el-radio v-for="(outline, index) in outlines" :key="index" :label="outline">
            <pre>{{ outline }}</pre>
          </el-radio>
        </el-radio-group>
      </div>
      
      <!-- 生成的文章 -->
      <div v-if="article" class="section">
        <h3>生成的文章</h3>
        <el-card class="article-card">
          <pre class="article-content">{{ article }}</pre>
        </el-card>
        <el-button type="success" @click="copyArticle" style="margin-top: 20px">
          复制文章
        </el-button>
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
  llmProvider: 'deepseek',
  topic: '',
  keywords: ''
})

const loadingTitles = ref(false)
const loadingOutlines = ref(false)
const loadingArticle = ref(false)
const threadId = ref('')
const titles = ref([])
const outlines = ref([])
const article = ref('')
const selectedTitle = ref('')
const selectedOutline = ref('')

const resetAfterTopicChange = () => {
  threadId.value = ''
  titles.value = []
  outlines.value = []
  article.value = ''
  selectedTitle.value = ''
  selectedOutline.value = ''
}

const handleGenerateTitles = async () => {
  if (!form.value.topic || !form.value.keywords) {
    ElMessage.warning('请填写主题和关键词')
    return
  }

  resetAfterTopicChange()
  loadingTitles.value = true
  try {
    const params = {
      topic: form.value.topic,
      keywords: form.value.keywords,
      tenantId: form.value.tenantId,
      collectionName: form.value.collectionName,
      llmProvider: form.value.llmProvider
    }
    const response = await axios.post('/api/v1/generate/titles', null, { params })

    threadId.value = response.data.thread_id
    titles.value = response.data.titles || []
    if (titles.value.length > 0) {
      selectedTitle.value = titles.value[0]
      ElMessage.success('标题已生成，请选择一个标题并继续生成大纲')
    } else {
      ElMessage.warning('没有生成标题，请重试')
    }
  } catch (error) {
    ElMessage.error('生成标题失败: ' + (error.response?.data?.message || error.message))
  } finally {
    loadingTitles.value = false
  }
}

const handleGenerateOutlines = async () => {
  if (!threadId.value || !selectedTitle.value) {
    ElMessage.warning('请先生成并选择标题')
    return
  }

  loadingOutlines.value = true
  article.value = ''
  selectedOutline.value = ''
  try {
    const params = {
      threadId: threadId.value,
      selectedTitle: selectedTitle.value
    }
    const response = await axios.post('/api/v1/generate/outlines', null, { params })
    outlines.value = response.data.outlines || []
    if (outlines.value.length > 0) {
      selectedOutline.value = outlines.value[0]
      ElMessage.success('大纲已生成，请选择一套并生成文章')
    } else {
      ElMessage.warning('没有生成大纲，请重试')
    }
  } catch (error) {
    ElMessage.error('生成大纲失败: ' + (error.response?.data?.message || error.message))
  } finally {
    loadingOutlines.value = false
  }
}

const handleGenerateArticle = async () => {
  if (!threadId.value || !selectedOutline.value) {
    ElMessage.warning('请先选择大纲')
    return
  }

  loadingArticle.value = true
  try {
    const params = {
      threadId: threadId.value,
      selectedOutline: selectedOutline.value
    }
    const response = await axios.post('/api/v1/generate/article', null, { params })
    article.value = response.data.article || ''
    ElMessage.success('文章生成成功')
  } catch (error) {
    ElMessage.error('生成文章失败: ' + (error.response?.data?.message || error.message))
  } finally {
    loadingArticle.value = false
  }
}

const copyArticle = () => {
  if (!article.value) {
    ElMessage.warning('暂无可复制内容')
    return
  }
  navigator.clipboard.writeText(article.value)
  ElMessage.success('已复制到剪贴板')
}
</script>

<style scoped>
.generate-page {
  max-width: 900px;
  margin: 0 auto;
}

.generate-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.section {
  margin-top: 40px;
}

.section h3 {
  margin-bottom: 20px;
  color: #303133;
}

.article-card {
  background-color: #f5f7fa;
}

.article-content {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 16px;
  margin: 0;
}

pre {
  white-space: pre-wrap;
  margin: 0;
}
</style>
