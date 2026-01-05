<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>收藏夹列表</span>
          <el-button type="primary" @click="showCreateDialog = true">创建收藏夹</el-button>
        </div>
      </template>
      <el-table :data="collections || []" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="goToCollection(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="collections && collections.length === 0" description="暂无收藏夹" />
    </el-card>

    <el-dialog v-model="showCreateDialog" title="创建收藏夹" width="500px">
      <el-form :model="newCollection" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="newCollection.name" placeholder="请输入收藏夹名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newCollection.description"
            type="textarea"
            :rows="4"
            placeholder="请输入描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createCollection">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

interface Collection {
  id: number
  name: string
  description: string | null
  created_at: string
}

const config = useRuntimeConfig()
const router = useRouter()

const collections = ref<Collection[]>([])

// 加载数据
const loadCollections = async () => {
  try {
    const data = await $fetch<Collection[]>(`${config.public.apiBase}/collections`)
    collections.value = data || []
  } catch (error) {
    console.error('加载收藏夹列表失败:', error)
    collections.value = []
  }
}

// 初始加载
await loadCollections()

const showCreateDialog = ref(false)
const newCollection = ref({
  name: '',
  description: null as string | null
})

const createCollection = async () => {
  if (!newCollection.value.name.trim()) {
    ElMessage.warning('请输入收藏夹名称')
    return
  }

  try {
    await $fetch(`${config.public.apiBase}/collections`, {
      method: 'POST',
      body: {
        name: newCollection.value.name,
        description: newCollection.value.description
      }
    })
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    newCollection.value = {
      name: '',
      description: null
    }
    // 重新加载数据
    await loadCollections()
  } catch (error) {
    ElMessage.error('创建失败')
    console.error(error)
  }
}

const goToCollection = (id: number) => {
  router.push(`/collections/${id}`)
}
</script>
