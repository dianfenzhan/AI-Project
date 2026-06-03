<template>
  <div class="upload-page">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>文档上传</span>
        </div>
      </template>
      
      <el-form :model="form" label-width="120px">
        <el-form-item label="租户ID">
          <el-input v-model="form.tenantId" placeholder="请输入租户ID" />
        </el-form-item>
        <el-form-item label="集合名称">
          <el-input v-model="form.collectionName" placeholder="请输入集合名称" />
        </el-form-item>
        <el-form-item label="选择文档">
          <el-upload
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            accept=".pdf,.md,.txt,.docx"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF, MD, TXT, DOCX 格式
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleUpload" :loading="loading">
            上传并索引
          </el-button>
        </el-form-item>
      </el-form>
      
      <el-alert
        v-if="uploadResult"
        :title="uploadResult"
        type="success"
        :closable="false"
        style="margin-top: 20px"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const form = ref({
  tenantId: 'default',
  collectionName: 'default'
})

const selectedFile = ref(null)
const loading = ref(false)
const uploadResult = ref('')

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  if (!form.value.tenantId || !form.value.collectionName) {
    ElMessage.warning('请填写租户ID和集合名称')
    return
  }
  
  loading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('tenantId', form.value.tenantId)
  formData.append('collectionName', form.value.collectionName)
  
  try {
    const response = await axios.post('/api/v1/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    uploadResult.value = `上传成功！处理了 ${response.data.chunks_count} 个文本块`
    ElMessage.success('上传成功')
  } catch (error) {
    ElMessage.error('上传失败: ' + error.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.upload-page {
  max-width: 800px;
  margin: 0 auto;
}

.upload-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}
</style>
