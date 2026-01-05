<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h2>{{ collection?.name || '收藏夹' }}</h2>
          <el-button @click="goBack">返回</el-button>
        </div>
        <div v-if="collection?.description" style="margin-top: 10px; color: #666">
          {{ collection.description }}
        </div>
      </template>

      <div style="margin-bottom: 20px">
        <el-button type="primary" @click="showAddDialog = true">添加番剧到收藏夹</el-button>
      </div>

      <el-row :gutter="20" v-if="animeList && animeList.length > 0">
        <el-col :span="6" v-for="anime in animeList" :key="anime.id" style="margin-bottom: 20px">
          <el-card shadow="hover" @click="goToAnime(anime.id)" style="cursor: pointer">
            <template #header>
              <div style="font-weight: bold; font-size: 16px">{{ anime.title }}</div>
            </template>
            <div>
              <div v-if="anime.start_date">开播日期: {{ anime.start_date }}</div>
              <div v-if="anime.total_episodes">总集数: {{ anime.total_episodes }}</div>
              <div v-if="anime.source_id">来源ID: {{ anime.source_id }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-else description="暂无番剧" />
    </el-card>

    <el-dialog v-model="showAddDialog" title="添加番剧到收藏夹" width="500px">
      <el-form label-width="100px">
        <el-form-item label="选择番剧" required>
          <el-select
            v-model="selectedAnimeId"
            placeholder="请选择番剧"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="anime in allAnimeList"
              :key="anime.id"
              :label="anime.title"
              :value="anime.id"
            />
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
import { ElMessage } from 'element-plus'

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

// 获取所有收藏夹以查找当前收藏夹信息（由于没有单独的 GET /collections/{id}）
const collections = ref<Collection[]>([])
const animeList = ref<Anime[]>([])
const allAnimeList = ref<Anime[]>([])

const loadCollections = async () => {
  try {
    const data = await $fetch<Collection[]>(`${config.public.apiBase}/collections`)
    collections.value = data || []
  } catch (error) {
    console.error('加载收藏夹列表失败:', error)
    collections.value = []
  }
}

const loadAnimeList = async () => {
  try {
    const data = await $fetch<Anime[]>(
      `${config.public.apiBase}/collections/${collectionId}/anime`
    )
    animeList.value = data || []
  } catch (error) {
    console.error('加载收藏夹番剧列表失败:', error)
    animeList.value = []
  }
}

const loadAllAnimeList = async () => {
  try {
    const data = await $fetch<Anime[]>(`${config.public.apiBase}/anime`)
    allAnimeList.value = data || []
  } catch (error) {
    console.error('加载所有番剧列表失败:', error)
    allAnimeList.value = []
  }
}

// 初始加载
await Promise.all([
  loadCollections(),
  loadAnimeList(),
  loadAllAnimeList()
])

const collection = computed(() => {
  return collections.value?.find(c => c.id === collectionId)
})

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
    await loadAnimeList()
  } catch (error) {
    ElMessage.error('添加失败')
    console.error(error)
  }
}

const goBack = () => {
  router.push('/collections')
}

const goToAnime = (id: number) => {
  router.push(`/anime/${id}`)
}
</script>
