<template>
  <div class="system-upload">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>系统级文档上传</span>
          <el-tag type="warning" effect="plain">所有租户共享可检索</el-tag>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="intro-alert"
        title="系统级文档用于存放通用 SEO 方法论、行业资料等，上传后所有租户在搜索与文章生成时均可引用。"
      />

      <el-form label-width="120px">
        <el-form-item label="共享集合名" required>
          <el-input
            v-model="collectionName"
            placeholder="如 system_kb"
            style="width: 360px"
          />
          <div class="field-tip">系统级文档写入共享库（tenant_id = __system__），与租户集合相互隔离。</div>
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
            <div class="el-upload__text">拖拽文件到此处或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 PDF, MD, TXT, DOCX 格式</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="warning" @click="handleUpload" :loading="loading">
            上传并索引（系统级）
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

const collectionName = ref('system_kb')
const selectedFile = ref(null)
const loading = ref(false)
const uploadResult = ref('')

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleUpload = async () => {
  if (!collectionName.value.trim()) {
    ElMessage.warning('请填写共享集合名称')
    return
  }
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  loading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('scope', 'system')
  formData.append('tenantId', 'system')
  formData.append('collectionName', collectionName.value.trim())

  try {
    const response = await axios.post('/api/v1/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    uploadResult.value = `上传成功！系统级共享库「${collectionName.value}」，处理了 ${response.data.chunks_count} 个文本块`
    ElMessage.success('系统级文档上传成功')
  } catch (error) {
    ElMessage.error('上传失败: ' + (error.response?.data?.message || error.message))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 600;
}

.intro-alert {
  margin-bottom: 24px;
}

.field-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
