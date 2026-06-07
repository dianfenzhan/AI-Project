import { ref, onMounted } from 'vue'
import axios from 'axios'

export function useTenants() {
  const tenants = ref([])
  const loading = ref(false)

  const fetchTenants = async () => {
    loading.value = true
    try {
      const { data } = await axios.get('/api/v1/tenants')
      tenants.value = data
    } catch {
      tenants.value = []
    } finally {
      loading.value = false
    }
  }

  onMounted(fetchTenants)

  return { tenants, loading, fetchTenants }
}
