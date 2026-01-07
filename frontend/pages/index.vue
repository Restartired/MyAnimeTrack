<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>番剧列表</span>
          <div style="display: flex; gap: 10px; align-items: center;">
            <el-select v-model="sortBy" placeholder="排序" size="small" style="width: 120px; margin-right: 10px;">
              <el-option label="默认(上传时间)" value="newest" />
              <el-option label="最早上传" value="oldest" />
              <el-option label="开播日期" value="air_date" />
              <el-option label="标题" value="title" />
            </el-select>

            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button value="card">卡片视图</el-radio-button>
              <el-radio-button value="list">列表视图</el-radio-button>
            </el-radio-group>

            <el-button type="primary" size="small" @click="showCreateDialog = true">添加番剧</el-button>
          </div>
        </div>
      </template>
      <div v-loading="pending">

        <!-- 卡片视图 -->
        <div v-if="viewMode === 'card'">
          <el-row :gutter="20" v-if="!pending && sortedAnimeList && sortedAnimeList.length > 0">
            <el-col :span="6" v-for="anime in sortedAnimeList" :key="anime.id" style="margin-bottom: 20px">
              <el-card shadow="hover" @click="goToAnime(anime.id)" style="cursor: pointer">
                <template #header>
                  <div style="font-weight: bold; font-size: 16px">{{ anime.title }}</div>
                </template>
                <div>
                  <div v-if="anime.start_date">开播日期: {{ anime.start_date }}</div>
                  <div v-if="anime.total_episodes">总集数: {{ anime.total_episodes }}</div>
                  <div v-if="anime.created_at" style="color: #999; font-size: 12px; margin-top: 5px;">
                    上传于: {{ formatDate(anime.created_at) }}
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
          <el-empty v-else-if="!pending" description="暂无番剧" />
        </div>

        <!-- 列表视图 -->
        <div v-else>
          <el-table v-if="!pending && sortedAnimeList && sortedAnimeList.length > 0" :data="sortedAnimeList"
            style="width: 100%" @row-click="goToAnimeByRow">
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="start_date" label="开播日期" width="120" />
            <el-table-column prop="total_episodes" label="总集数" width="100" />
            <el-table-column label="上传时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="danger" size="small" @click.stop="deleteAnimeInList(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else-if="!pending" description="暂无番剧" />
        </div>

        <div v-if="error" style="text-align: center; padding: 20px; color: #f56c6c;">
          加载失败，请刷新页面重试
        </div>
      </div>
    </el-card>

    <el-dialog v-model="showCreateDialog" title="添加番剧" width="600px">
      <!-- (Dialog content remains exact same) -->
      <el-tabs v-model="activeTab">
        <el-tab-pane label="手动输入" name="manual">
          <el-form :model="newAnime" label-width="100px" style="margin-top: 20px">
            <el-form-item label="标题" required>
              <el-input v-model="newAnime.title" placeholder="请输入番剧标题" />
            </el-form-item>
            <el-form-item label="开播日期">
              <el-date-picker v-model="newAnime.start_date" type="date" placeholder="选择日期" format="YYYY-MM-DD"
                value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
            <el-form-item label="总集数">
              <el-input-number v-model="newAnime.total_episodes" :min="1" />
            </el-form-item>
            <el-form-item label="来源ID">
              <el-input v-model="newAnime.source_id" placeholder="可选" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="从 Bangumi 搜索" name="search">
          <div style="margin-top: 20px">
            <el-form inline>
              <el-form-item label="搜索">
                <el-input v-model="searchQuery" placeholder="输入番剧名称" @keyup.enter="searchBangumi"
                  style="width: 300px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="searchBangumi" :loading="searching">搜索</el-button>
              </el-form-item>
            </el-form>

            <div v-if="searchError" style="color: #f56c6c; margin: 10px 0;">
              {{ searchError }}
            </div>

            <div v-if="searchResults.length > 0" style="margin-top: 20px; max-height: 400px; overflow-y: auto;">
              <el-card v-for="result in searchResults" :key="result.id" shadow="hover"
                style="margin-bottom: 10px; cursor: pointer" @click="selectSearchResult(result)">
                <div style="display: flex;">
                  <div v-if="result.cover_image" style="margin-right: 15px;">
                    <img :src="result.cover_image"
                      style="width: 80px; height: 112px; object-fit: cover; border-radius: 4px;" />
                  </div>
                  <div style="flex: 1;">
                    <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">
                      {{ result.title }}
                    </div>
                    <div v-if="result.name_jp && result.name_jp !== result.title"
                      style="color: #666; margin-bottom: 5px;">
                      {{ result.name_jp }}
                    </div>
                    <div style="color: #909399; font-size: 12px;">
                      <div v-if="result.start_date">开播日期: {{ result.start_date }}</div>
                      <div v-if="result.total_episodes">集数: {{ result.total_episodes }}</div>
                    </div>
                    <el-button size="small" type="primary" style="margin-top: 8px;"
                      @click.stop="selectSearchResult(result)">
                      选择
                    </el-button>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createAnime">确定</el-button>
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
}

interface BangumiSearchResult {
  id: number
  title: string
  name_jp?: string
  name_cn?: string
  start_date: string | null
  total_episodes: number | null
  cover_image: string | null
  summary?: string
  source_id: string
}

const config = useRuntimeConfig()
const router = useRouter()
const viewMode = ref('card')
const sortBy = ref('newest') // newest, oldest, air_date, title

const { data: animeList, pending, error, refresh } = await useAsyncData<Anime[]>(
  'anime-list',
  () => $fetch(`${config.public.apiBase}/anime`)
)

// Sorting Logic
const sortedAnimeList = computed(() => {
  if (!animeList.value) return []
  const list = [...animeList.value]

  switch (sortBy.value) {
    case 'newest':
      // Backend already sends sorted by created_at DESC as default usually, but ensuring here
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
  }
  return list
})

const showCreateDialog = ref(false)
const activeTab = ref('manual')
const searchQuery = ref('')
const searchResults = ref<BangumiSearchResult[]>([])
const searching = ref(false)
const searchError = ref('')

const newAnime = ref({
  title: '',
  start_date: null as string | null,
  total_episodes: null as number | null,
  source_id: null as string | null
})

const searchBangumi = async () => {
  // ... search logic
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  searching.value = true
  searchError.value = ''
  searchResults.value = []

  try {
    const response = await $fetch<{ results: BangumiSearchResult[], error?: string }>(
      `${config.public.apiBase}/bangumi/search`,
      {
        params: { query: searchQuery.value }
      }
    )

    if (response.error) {
      searchError.value = response.error
      ElMessage.error(response.error)
    } else {
      searchResults.value = response.results || []
      if (searchResults.value.length === 0) {
        ElMessage.info('未找到相关番剧')
      }
    }
  } catch (err) {
    console.error('搜索失败:', err)
    searchError.value = '搜索失败，请稍后重试'
    ElMessage.error('搜索失败')
  } finally {
    searching.value = false
  }
}

const selectSearchResult = (result: BangumiSearchResult) => {
  newAnime.value = {
    title: result.title,
    start_date: result.start_date,
    total_episodes: result.total_episodes,
    source_id: result.source_id
  }
  activeTab.value = 'manual'
  ElMessage.success('已填充数据，请确认后点击确定')
}

const createAnime = async () => {
  if (!newAnime.value.title.trim()) {
    ElMessage.warning('请输入番剧标题')
    return
  }

  try {
    await $fetch(`${config.public.apiBase}/anime`, {
      method: 'POST',
      body: {
        title: newAnime.value.title,
        start_date: newAnime.value.start_date,
        total_episodes: newAnime.value.total_episodes,
        source_id: newAnime.value.source_id
      }
    })
    ElMessage.success('添加成功')
    showCreateDialog.value = false
    newAnime.value = {
      title: '',
      start_date: null,
      total_episodes: null,
      source_id: null
    }
    searchQuery.value = ''
    searchResults.value = []
    activeTab.value = 'manual'
    refresh()
  } catch (error) {
    ElMessage.error('添加失败')
    console.error(error)
  }
}

const goToAnime = (id: number) => {
  router.push(`/anime/${id}`)
}

const goToAnimeByRow = (row: Anime) => {
  goToAnime(row.id)
}

const deleteAnimeInList = (anime: Anime) => {
  ElMessageBox.confirm(
    '确定要删除这个番剧吗？删除后将无法恢复，包括相关的剧集和评价记录。',
    '警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await $fetch(`${config.public.apiBase}/anime/${anime.id}`, {
          method: 'DELETE',
        })
        ElMessage.success('番剧已删除')
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
