<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h2>{{ collection?.name || '收藏夹' }}</h2>
          <div style="display: flex; gap: 10px;">
            <el-button type="danger" @click="deleteCollection">删除收藏夹</el-button>
            <el-button @click="goBack">返回</el-button>
          </div>
        </div>
        <div v-if="collection?.description" style="margin-top: 10px; color: #666">
          {{ collection.description }}
        </div>
      </template>

      <div style="margin-bottom: 20px">
        <el-button type="primary" @click="showAddDialog = true">添加番剧到收藏夹</el-button>
      </div>

      <div v-loading="pending">
        <el-table v-if="!pending && animeList && animeList.length > 0" :data="animeList" style="width: 100%">
          <el-table-column label="番剧名称">
            <template #default="{ row }">
              <span style="font-weight: bold; cursor: pointer; color: #409EFF" @click="goToAnime(row.id)">{{ row.title
                }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="start_date" label="开播日期" width="150" />
          <el-table-column prop="total_episodes" label="总集数" width="120" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="removeAnime(row)">移出</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else-if="!pending" description="暂无番剧" />
      </div>
    </el-card>

    <el-dialog v-model="showAddDialog" title="添加番剧到收藏夹" width="500px">
      <el-form label-width="100px">
        <el-form-item label="选择番剧" required>
          <el-select v-model="selectedAnimeId" placeholder="请选择番剧" filterable style="width: 100%">
            <el-option v-for="anime in allAnimeList" :key="anime.id" :label="anime.title" :value="anime.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addAnimeToCollection">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'

interface Collection {
  id: number
  name: string
  description: string | null
  created_at: string
}

interface Anime {
  id: number
  title: string
  start_date: string | null
  total_episodes: number | null
  created_at: string
  source_id: string | null
}

const route = useRoute()
const config = useRuntimeConfig()
const router = useRouter()
const collectionId = parseInt(route.params.id as string)

// Load collection list to match ID (could be optimized with a dedicated GET endpoint)
const { data: collections } = await useAsyncData<Collection[]>(
  'collections-list',
  () => $fetch(`${config.public.apiBase}/collections`)
)

const collection = computed(() => {
  return collections.value?.find(c => c.id === collectionId)
})

// Load anime list for this collection
const { data: animeList, pending, refresh } = await useAsyncData<Anime[]>(
  `collection-${collectionId}-anime`,
  () => $fetch(`${config.public.apiBase}/collections/${collectionId}/anime`)
)

// Load All anime for the dropdown
const { data: allAnimeList } = await useAsyncData<Anime[]>(
  'all-anime-list',
  () => $fetch(`${config.public.apiBase}/anime`)
)

const showAddDialog = ref(false)
const selectedAnimeId = ref<number | null>(null)

const addAnimeToCollection = async () => {
  if (!selectedAnimeId.value) {
    ElMessage.warning('请选择番剧')
    return
  }

  try {
    await $fetch(`${config.public.apiBase}/collections/${collectionId}/anime`, {
      method: 'POST',
      body: {
        anime_id: selectedAnimeId.value
      }
    })
    ElMessage.success('添加成功')
    showAddDialog.value = false
    selectedAnimeId.value = null
    refresh()
  } catch (error) {
    ElMessage.error('添加失败')
    console.error(error)
  }
}

const removeAnime = (anime: Anime) => {
  ElMessageBox.confirm(
    `确定要将 "${anime.title}" 移出收藏夹吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await $fetch(`${config.public.apiBase}/collections/${collectionId}/anime/${anime.id}`, {
        method: 'DELETE'
      })
      ElMessage.success('已移出')
      refresh()
    } catch (error) {
      ElMessage.error('移出失败')
      console.error(error)
    }
  }).catch(() => { })
}

const deleteCollection = () => {
  ElMessageBox.confirm(
    `确定要删除收藏夹 "${collection.value?.name}" 吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await $fetch(`${config.public.apiBase}/collections/${collectionId}`, {
          method: 'DELETE',
        })
        ElMessage.success('删除成功')
        router.push('/collections')
      } catch (error) {
        ElMessage.error('删除失败')
        console.error(error)
      }
    })
    .catch(() => {
      // 取消
    })
}

const goBack = () => {
  router.push('/collections')
}

const goToAnime = (id: number) => {
  router.push(`/anime/${id}`)
}
</script>
