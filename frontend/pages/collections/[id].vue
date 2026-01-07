<template>
  <div v-loading="pending">
    <div v-if="collection" class="collection-header">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
           <h2>{{ collection.name }}</h2>
           <p style="color: #666; margin-bottom: 5px;">{{ collection.description }}</p>
           <p style="color: #999; font-size: 12px;">创建时间: {{ formatDate(collection.created_at) }}</p>
        </div>
        <div style="text-align: right;">
           <el-button type="primary" @click="showEditDialog = true">编辑收藏夹</el-button>
        </div>
      </div>
    </div>
    
    <el-card v-if="collection">
        <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
                <span>番剧列表</span>
                <el-select v-model="sortBy" placeholder="排序" size="small" style="width: 120px;">
                    <el-option label="默认(上传时间)" value="newest" />
                    <el-option label="最早上传" value="oldest" />
                    <el-option label="开播日期" value="air_date" />
                    <el-option label="标题" value="title" />
                    <el-option label="我的评分" value="rating" />
                </el-select>
            </div>
        </template>

      <el-table :data="sortedAnime || []" style="width: 100%" @row-click="goToAnime">
         <el-table-column label="封面" width="80">
            <template #default="{ row }">
                <img 
                    v-if="row.cover_image_url" 
                    :src="row.cover_image_url" 
                    style="width: 50px; height: 70px; object-fit: cover; border-radius: 4px;"
                />
                <div v-else style="width: 50px; height: 70px; background: #eaecf1; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #909399;">
                    无图
                </div>
            </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="start_date" label="开播日期" width="120" />
        <el-table-column prop="total_episodes" label="总集数" width="100" />
        <el-table-column label="评分" width="100" sortable :sort-method="(a, b) => (a.my_score || 0) - (b.my_score || 0)">
            <template #default="{ row }">
                <span v-if="row.my_score" style="color: #ff9900; font-weight: bold;">{{ row.my_score }} 分</span>
                <span v-else style="color: #ccc;">-</span>
            </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180">
             <template #default="{ row }">
                 {{ formatDate(row.created_at) }}
             </template>
         </el-table-column>
        <el-table-column label="操作" width="100">
            <template #default="{ row }">
                 <el-button size="small" type="danger" @click.stop="removeAnime(row)">移除</el-button>
            </template>
        </el-table-column>
      </el-table>
        <el-empty v-if="!sortedAnime || sortedAnime.length === 0" description="收藏夹为空" />
    </el-card>
    
    <div v-if="error">
        <el-empty description="收藏夹不存在" />
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="showEditDialog" title="编辑收藏夹" width="500px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateCollection">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'

interface Anime {
  id: number
  title: string
  start_date: string | null
  total_episodes: number | null
  created_at: string
  source_id: string | null
  cover_image_url: string | null
  my_score: number | null
}

interface Collection {
    id: number
    name: string
    description: string
    created_at: string
}

const route = useRoute()
const router = useRouter()
const config = useRuntimeConfig()
const collectionId = route.params.id

const sortBy = ref('newest')

// Fetch Collection Details
const { data: collection, refresh: refreshCollection, error: collError } = await useAsyncData<Collection>(
    `collection-${collectionId}`,
    () => $fetch<Collection[]>(`${config.public.apiBase}/collections`).then(list => list.find(c => c.id == parseInt(collectionId as string)) as Collection)
)

// Fetch Anime in Collection
const { data: animeList, pending, error, refresh: refreshAnime } = await useAsyncData<Anime[]>(
  `collection-anime-${collectionId}`,
  () => $fetch<Anime[]>(`${config.public.apiBase}/collections/${collectionId}/anime`)
)

const sortedAnime = computed(() => {
    if (!animeList.value) return []
    const list = [...animeList.value]
    
    switch (sortBy.value) {
        case 'newest':
            return list // Default from backend is created_at DESC
        case 'oldest':
            return list.reverse()
        case 'air_date':
            return list.sort((a, b) => {
                if (!a.start_date) return 1
                if (!b.start_date) return -1
                return a.start_date.localeCompare(b.start_date)
            })
        case 'title':
            return list.sort((a, b) => a.title.localeCompare(b.title, 'zh'))
        case 'rating':
            return list.sort((a, b) => (b.my_score || 0) - (a.my_score || 0))
    }
    return list
})

const goToAnime = (row: Anime) => {
  router.push(`/anime/${row.id}`)
}

const removeAnime = async (anime: Anime) => {
    ElMessageBox.confirm(
    `确定要从收藏夹中移除 "${anime.title}" 吗？`,
    '移除确认',
    {
      confirmButtonText: '移除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
        try {
            await $fetch(`${config.public.apiBase}/collections/${collectionId}/anime/${anime.id}`, {
                method: 'DELETE'
            })
            ElMessage.success('已移除')
            refreshAnime()
        } catch (e) {
            ElMessage.error('移除失败')
        }
  }).catch(()=>{})
}

// Edit Logic
const showEditDialog = ref(false)
const editForm = ref({ name: '', description: '' })

watch(collection, (newVal) => {
    if (newVal) {
        editForm.value = { 
            name: newVal.name, 
            description: newVal.description || '' 
        }
    }
}, { immediate: true })

const updateCollection = async () => {
    if (!editForm.value.name) return
    try {
        await $fetch(`${config.public.apiBase}/collections/${collectionId}`, {
            method: 'PUT',
            body: editForm.value
        })
        ElMessage.success('更新成功')
        showEditDialog.value = false
        refreshCollection() 
        // Need to force update list in parent if cache used? 
        // Ideally we also refresh lists, but this is detail page.
    } catch(e) {
        ElMessage.error('更新失败')
    }
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

<style scoped>
.collection-header {
  background-color: #fff;
  padding: 20px;
  margin-bottom: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}
</style>
