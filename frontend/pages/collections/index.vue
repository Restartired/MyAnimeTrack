<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>收藏夹列表</span>
          <el-button type="primary" @click="openCreateDialog">创建收藏夹</el-button>
        </div>
      </template>
      <div v-loading="pending">
        <el-table v-if="!pending && collections && collections.length > 0" :data="collections" style="width: 100%"
          @row-click="goToCollectionByRow" row-class-name="clickable-row">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="description" label="描述" />
          <el-table-column label="创建时间" width="200">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click.stop="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" size="small" @click.stop="deleteCollection(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else-if="!pending" description="暂无收藏夹" />
      </div>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="isEditMode ? '编辑收藏夹' : '创建收藏夹'" width="500px">
      <el-form :model="collectionForm" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="collectionForm.name" placeholder="请输入收藏夹名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="collectionForm.description" type="textarea" :rows="4" placeholder="请输入描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submitCollection">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style>
.clickable-row {
  cursor: pointer;
}
</style>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'

interface Collection {
  id: number
  name: string
  description: string | null
  created_at: string
}

const config = useRuntimeConfig()
const router = useRouter()

const { data: collections, pending, refresh } = await useAsyncData<Collection[]>(
  'collections-list',
  () => $fetch(`${config.public.apiBase}/collections`)
)

const showDialog = ref(false)
const isEditMode = ref(false)
const editingId = ref<number | null>(null)
const collectionForm = ref({
  name: '',
  description: null as string | null
})

const openCreateDialog = () => {
  isEditMode.value = false
  editingId.value = null
  collectionForm.value = {
    name: '',
    description: null
  }
  showDialog.value = true
}

const openEditDialog = (row: Collection) => {
  isEditMode.value = true
  editingId.value = row.id
  collectionForm.value = {
    name: row.name,
    description: row.description
  }
  showDialog.value = true
}

const submitCollection = async () => {
  if (!collectionForm.value.name.trim()) {
    ElMessage.warning('请输入收藏夹名称')
    return
  }

  try {
    if (isEditMode.value && editingId.value) {
      // Edit
      await $fetch(`${config.public.apiBase}/collections/${editingId.value}`, {
        method: 'PUT',
        body: {
          name: collectionForm.value.name,
          description: collectionForm.value.description
        }
      })
      ElMessage.success('更新成功')
    } else {
      // Create
      await $fetch(`${config.public.apiBase}/collections`, {
        method: 'POST',
        body: {
          name: collectionForm.value.name,
          description: collectionForm.value.description
        }
      })
      ElMessage.success('创建成功')
    }

    showDialog.value = false
    refresh()
  } catch (error) {
    ElMessage.error(isEditMode.value ? '更新失败' : '创建失败')
    console.error(error)
  }
}

const goToCollectionByRow = (row: Collection) => {
  router.push(`/collections/${row.id}`)
}

const deleteCollection = (row: Collection) => {
  ElMessageBox.confirm(
    `确定要删除收藏夹 "${row.name}" 吗？`,
    '警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await $fetch(`${config.public.apiBase}/collections/${row.id}`, {
          method: 'DELETE',
        })
        ElMessage.success('收藏夹已删除')
        refresh()
      } catch (error) {
        ElMessage.error('删除失败')
        console.error(error)
      }
    })
    .catch(() => {
    })
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}
</script>
