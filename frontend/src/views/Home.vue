<template>
  <div class="home-page">
    <el-card class="context-card" shadow="never">
      <template #header>
        <span class="context-title">搜索 / 生成上下文</span>
      </template>
      <el-form :inline="true">
        <el-form-item label="当前租户">
          <el-select
            v-model="shared.tenantId"
            placeholder="请选择租户"
            style="width: 320px"
            :loading="tenantsLoading"
            filterable
            @change="handleSharedTenantChange"
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
          <el-input v-model="shared.collectionName" style="width: 180px" disabled />
        </el-form-item>
      </el-form>
    </el-card>

    <el-tabs v-model="activeTab" class="module-tabs" type="border-card">
      <el-tab-pane label="租户文档上传" name="tenant-upload">
        <TenantUploadPanel
          :tenants="tenants"
          :tenants-loading="tenantsLoading"
          :tenant-id="shared.tenantId"
          :collection-name="shared.collectionName"
          @update:tenant-id="onTenantUploadChange"
          @update:collection-name="(v) => (shared.collectionName = v)"
        />
      </el-tab-pane>
      <el-tab-pane label="系统文档上传" name="system-upload">
        <SystemUploadPanel />
      </el-tab-pane>
      <el-tab-pane label="知识库搜索" name="search">
        <SearchPanel :tenant-id="shared.tenantId" :collection-name="shared.collectionName" />
      </el-tab-pane>
      <el-tab-pane label="文章生成" name="generate">
        <GeneratePanel :tenant-id="shared.tenantId" :collection-name="shared.collectionName" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTenants } from '../composables/useTenants'
import TenantUploadPanel from './TenantUpload.vue'
import SystemUploadPanel from './SystemUpload.vue'
import SearchPanel from './Search.vue'
import GeneratePanel from './Generate.vue'

const route = useRoute()
const router = useRouter()
const { tenants, loading: tenantsLoading } = useTenants()

const shared = ref({
  tenantId: '',
  collectionName: ''
})

watch(tenants, (list) => {
  if (list.length && !shared.value.tenantId) {
    shared.value.tenantId = list[0].tenantId
    shared.value.collectionName = list[0].collectionName
  }
}, { immediate: true })

const tabNames = ['tenant-upload', 'system-upload', 'search', 'generate']
const legacyTabMap = { upload: 'tenant-upload' }

const resolveTab = (tab) => {
  if (tabNames.includes(tab)) return tab
  if (legacyTabMap[tab]) return legacyTabMap[tab]
  return 'tenant-upload'
}

const activeTab = ref(resolveTab(route.query.tab))

const handleSharedTenantChange = (tenantId) => {
  const tenant = tenants.value.find((t) => t.tenantId === tenantId)
  if (tenant) shared.value.collectionName = tenant.collectionName
}

const onTenantUploadChange = (tenantId) => {
  shared.value.tenantId = tenantId
  handleSharedTenantChange(tenantId)
}

watch(activeTab, (tab) => {
  if (route.query.tab !== tab) {
    router.replace({ query: { ...route.query, tab } })
  }
})

watch(
  () => route.query.tab,
  (tab) => {
    if (tab) {
      const resolved = resolveTab(tab)
      if (resolved !== activeTab.value) activeTab.value = resolved
    }
  }
)
</script>

<style scoped>
.home-page {
  width: 100%;
}

.context-card {
  margin-bottom: 20px;
}

.context-title {
  font-weight: 600;
}

.module-tabs :deep(.el-tabs__content) {
  padding: 24px 8px 8px;
}
</style>
