<template>
  <div class="tenant-upload">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>租户级文档上传</span>
          <el-tag type="info" effect="plain">仅所选租户可检索</el-tag>
        </div>
      </template>

      <el-form label-width="120px">
        <el-form-item label="选择租户" required>
          <el-select
            v-model="selectedTenantId"
            placeholder="请选择租户"
            style="width: 360px"
            :loading="tenantsLoading"
            filterable
            @change="handleTenantChange"
          >
            <el-option
              v-for="t in tenants"
              :key="t.tenantId"
              :label="`${t.name}（${t.tenantId}）`"
              :value="t.tenantId"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="集合名称">
          <el-input v-model="collectionName" style="width: 360px" disabled />
          <div class="field-tip">集合名称随租户自动填充，与数据库 tenants 表一致。</div>
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
          <el-button type="primary" @click="handleUpload" :loading="loading">
            上传并索引（租户级）
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
import { ref, watch } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  tenants: { type: Array, default: () => [] },
  tenantsLoading: { type: Boolean, default: false },
  tenantId: { type: String, default: '' },
  collectionName: { type: String, default: '' }
})

const emit = defineEmits(['update:tenantId', 'update:collectionName'])

const selectedTenantId = ref(props.tenantId)
const collectionName = ref(props.collectionName)
const selectedFile = ref(null)
const loading = ref(false)
const uploadResult = ref('')

watch(
  () => props.tenantId,
  (id) => {
    if (id) selectedTenantId.value = id
  }
)

watch(
  () => props.collectionName,
  (name) => {
    if (name) collectionName.value = name
  }
)

const handleTenantChange = (tenantId) => {
  const tenant = props.tenants.find((t) => t.tenantId === tenantId)
  if (tenant) {
    collectionName.value = tenant.collectionName
    emit('update:tenantId', tenant.tenantId)
    emit('update:collectionName', tenant.collectionName)
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleUpload = async () => {
  if (!selectedTenantId.value) {
    ElMessage.warning('请先选择租户')
    return
  }
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  loading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('scope', 'tenant')
  formData.append('tenantId', selectedTenantId.value)
  formData.append('collectionName', collectionName.value)

  try {
    const response = await axios.post('/api/v1/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    uploadResult.value = `上传成功！租户：${selectedTenantId.value}，处理了 ${response.data.chunks_count} 个文本块`
    ElMessage.success('租户级文档上传成功')
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

.field-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
