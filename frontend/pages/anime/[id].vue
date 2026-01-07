<template>
  <div v-if="anime" v-loading="pending">
    <div style="position: relative;">
      <!-- Banner/Header with Image if available -->
      <el-card>
        <div style="display: flex;">
          <div v-if="anime.cover_image_url" style="margin-right: 20px;">
            <img :src="anime.cover_image_url"
              style="width: 200px; border-radius: 4px; box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);" />
          </div>
          <div style="flex: 1;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <h2 style="margin-top: 0;">{{ anime.title }}</h2>
              <div style="display: flex; gap: 10px;">
                <el-button v-if="anime.source_id" type="warning" plain @click="syncAnimeInfo" :loading="syncing">
                  更新信息
                </el-button>
                <el-button type="primary" @click="showAddToCollectionDialog = true">加入收藏夹</el-button>
                <el-button type="danger" @click="deleteAnime">删除番剧</el-button>
              </div>
            </div>

            <div style="margin-bottom: 20px; font-size: 14px; color: #555;">
              <div v-if="anime.start_date" style="margin-bottom: 5px;">开播日期: {{ anime.start_date }}</div>
              <div v-if="anime.total_episodes" style="margin-bottom: 5px;">总集数: {{ anime.total_episodes }}</div>
              <div v-if="anime.source_id" style="margin-bottom: 5px;">
                来源ID:
                <a v-if="anime.source_id.startsWith('BGM-')"
                  :href="`https://bangumi.tv/subject/${anime.source_id.split('-')[1]}`" target="_blank"
                  style="color: #409eff; text-decoration: none;">
                  {{ anime.source_id }} (点击跳转)
                </a>
                <span v-else>{{ anime.source_id }}</span>
              </div>
              <div v-if="anime.created_at" style="color: #999; font-size: 13px; margin-top: 10px;">
                上传时间: {{ formatDate(anime.created_at) }}
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>番剧总评</span>
      </template>
      <el-form :model="animeReview" label-width="100px">
        <el-form-item label="评分">
          <el-rate v-model="animeReview.score" :max="10" show-score />
        </el-form-item>
        <el-form-item label="评价">
          <el-input v-model="animeReview.comment" type="textarea" :rows="4" placeholder="请输入评价" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveAnimeReview">保存评价</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div style="display: flex; gap: 15px; align-items: center;">
            <span style="font-weight: bold;">剧集列表</span>

            <!-- Filter -->
            <el-select v-model="episodeFilter" placeholder="类型" size="small" style="width: 120px;">
              <el-option label="全部" value="all" />
              <el-option label="正片" value="main" />
              <el-option label="SP" value="sp" />
              <el-option label="OVA" value="ova" />
              <el-option label="OP" value="op" />
              <el-option label="ED" value="ed" />
              <el-option label="其他" value="other" />
            </el-select>

            <!-- Sort -->
            <el-select v-model="episodeSortBy" placeholder="排序" size="small" style="width: 120px;">
              <el-option label="默认" value="default" />
              <el-option label="播出日期" value="air_date" />
              <el-option label="标题" value="title" />
            </el-select>
          </div>
          <el-button type="primary" @click="showEpisodeDialog = true">添加剧集</el-button>
        </div>
      </template>
      <el-table :data="filteredEpisodes || []" style="width: 100%" v-loading="episodesLoading">
        <el-table-column prop="episode_code" label="代码" width="100" />
        <el-table-column prop="episode_type" label="类型" width="80" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="air_date" label="播出日期" width="120" />
        <el-table-column label="评价" width="100">
          <template #default="{ row }">
            <!-- Reactivity fix: ensure we redraw based on row.score if modified locally -->
            <el-tag v-if="row.score" type="success" size="small">{{ row.score }}分</el-tag>
            <span v-else style="color: #bbb; font-size: 12px;">未评分</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openEpisodeReview(row)">评价</el-button>
            <el-button size="small" type="danger" @click="deleteEpisode(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="episodes && episodes.length === 0 && !episodesLoading" description="暂无剧集" />
    </el-card>

    <!-- Dialogs -->
    <el-dialog v-model="showAddToCollectionDialog" title="加入收藏夹" width="500px">
      <div v-if="collectionsLoading">加载中...</div>
      <el-form v-else label-width="100px">
        <el-form-item label="选择收藏夹" required>
          <el-select v-model="selectedCollectionId" placeholder="请选择收藏夹" style="width: 100%">
            <el-option v-for="c in collections" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddToCollectionDialog = false">取消</el-button>
        <el-button type="primary" @click="addToCollection">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEpisodeDialog" title="添加剧集" width="500px">
      <el-form :model="newEpisode" label-width="120px">
        <el-form-item label="剧集代码" required>
          <el-input v-model="newEpisode.episode_code" placeholder="如: E01, OVA1, SP01" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="newEpisode.episode_type" placeholder="选择类型" style="width: 100%">
            <el-option label="正片" value="main" />
            <el-option label="OVA" value="ova" />
            <el-option label="SP" value="sp" />
            <el-option label="电影" value="movie" />
            <el-option label="OP" value="op" />
            <el-option label="ED" value="ed" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="newEpisode.title" placeholder="可选" />
        </el-form-item>
        <el-form-item label="播出日期">
          <el-date-picker v-model="newEpisode.air_date" type="date" placeholder="选择日期" format="YYYY-MM-DD"
            value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEpisodeDialog = false">取消</el-button>
        <el-button type="primary" @click="createEpisode">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showReviewDialog" title="剧集评价" width="500px">
      <el-form :model="episodeReview" label-width="100px">
        <el-form-item label="评分">
          <el-rate v-model="episodeReview.score" :max="10" show-score />
        </el-form-item>
        <el-form-item label="评价">
          <el-input v-model="episodeReview.comment" type="textarea" :rows="4" placeholder="请输入评价" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReviewDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEpisodeReview">保存</el-button>
      </template>
    </el-dialog>
  </div>
  <div v-else>
    <el-empty description="番剧不存在" />
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
}

interface Episode {
  episode_code: string
  episode_type: string
  display_order: number // kept for typings but mostly unused
  title: string | null
  air_date: string | null
  score?: number
}

interface AnimeReview {
  score?: number
  comment?: string
  reviewed_at?: string
}

interface EpisodeReview {
  score?: number
  comment?: string
  reviewed_at?: string
}

interface Collection {
  id: number
  name: string
}

const route = useRoute()
const router = useRouter()
const config = useRuntimeConfig()

const animeId = computed(() => parseInt(route.params.id as string))

const { data: anime, pending, refresh: refreshAnime } = await useAsyncData<Anime>(
  `anime-${animeId.value}`,
  () => $fetch<Anime[]>(`${config.public.apiBase}/anime`).then(list => list.find(a => a.id === animeId.value) as Anime)
)

const episodes = ref<Episode[]>([])
const episodesLoading = ref(false)
const episodeSortBy = ref('default') // default (backend order), air_date, title
const episodeFilter = ref('all') // all, main, sp, ova, op, ed, other

const filteredEpisodes = computed(() => {
  if (!episodes.value) return []
  let list = [...episodes.value]

  // Filter
  if (episodeFilter.value !== 'all') {
    list = list.filter(e => e.episode_type === episodeFilter.value)
  }

  // Sort
  switch (episodeSortBy.value) {
    case 'default':
      // Backend order is prioritized 
      return list
    case 'air_date':
      return list.sort((a, b) => {
        if (!a.air_date) return 1
        if (!b.air_date) return -1
        return a.air_date.localeCompare(b.air_date)
      })
    case 'title':
      return list.sort((a, b) => {
        const titleA = a.title || ''
        const titleB = b.title || ''
        return titleA.localeCompare(titleB, 'zh')
      })
  }
  return list
})

const animeReview = ref<AnimeReview>({
  score: undefined,
  comment: undefined
})

const loadEpData = async () => {
  if (!animeId.value) return

  episodesLoading.value = true
  try {
    // Fetch episodes
    const eps = await $fetch<Episode[]>(`${config.public.apiBase}/anime/${animeId.value}/episodes`)

    episodes.value = eps.map(e => ({ ...e, score: undefined }))

    // Fetch reviews for all episodes
    Promise.all(eps.map(ep =>
      $fetch<EpisodeReview | null>(`${config.public.apiBase}/anime/${animeId.value}/episodes/${ep.episode_code}/review`)
        .then(r => {
          if (r && r.score) {
            const target = episodes.value.find(x => x.episode_code === ep.episode_code)
            if (target) target.score = r.score
          }
        })
        .catch(() => { })
    ))

  } catch (e) {
    console.error(e)
  } finally {
    episodesLoading.value = false
  }
}

const loadAnimeReview = async () => {
  if (!animeId.value) return
  try {
    const reviewData = await $fetch<AnimeReview | null>(`${config.public.apiBase}/anime/${animeId.value}/review`).catch(() => null)
    animeReview.value = reviewData ? {
      score: reviewData.score ?? undefined,
      comment: reviewData.comment ?? undefined
    } : { score: undefined, comment: undefined }
  } catch (e) { }
}

onMounted(() => {
  loadEpData()
  loadAnimeReview()
})

// Sync
const syncing = ref(false)
const syncAnimeInfo = async () => {
  syncing.value = true
  try {
    await $fetch(`${config.public.apiBase}/anime/${animeId.value}/sync`, { method: 'POST' })
    ElMessage.success('更新成功')
    refreshAnime()
    loadEpData()
  } catch (e) {
    ElMessage.error('更新失败')
  } finally {
    syncing.value = false
  }
}


// Add to Collection Logic
const showAddToCollectionDialog = ref(false)
const selectedCollectionId = ref<number | null>(null)
const collections = ref<Collection[]>([])
const collectionsLoading = ref(false)

const loadCollections = async () => {
  collectionsLoading.value = true
  try {
    const data = await $fetch<Collection[]>(`${config.public.apiBase}/collections`)
    collections.value = data || []
  } catch (e) {
    ElMessage.error('加载收藏夹列表失败')
  } finally {
    collectionsLoading.value = false
  }
}

// Load collections when dialog opens
watch(showAddToCollectionDialog, (val) => {
  if (val && collections.value.length === 0) {
    loadCollections()
  }
})

const addToCollection = async () => {
  if (!selectedCollectionId.value) {
    ElMessage.warning('请选择收藏夹')
    return
  }

  try {
    await $fetch(`${config.public.apiBase}/collections/${selectedCollectionId.value}/anime`, {
      method: 'POST',
      body: { anime_id: animeId.value }
    })
    ElMessage.success('已加入收藏夹')
    showAddToCollectionDialog.value = false
    selectedCollectionId.value = null
  } catch (e) {
    ElMessage.error('加入失败')
  }
}

const showEpisodeDialog = ref(false)
const newEpisode = ref({
  episode_code: '',
  episode_type: 'main',
  display_order: 1,
  title: null as string | null,
  air_date: null as string | null
})

const showReviewDialog = ref(false)
const currentEpisodeCode = ref('')
const episodeReview = ref<EpisodeReview>({
  score: undefined,
  comment: undefined
})

const createEpisode = async () => {
  if (!newEpisode.value.episode_code.trim()) {
    ElMessage.warning('请输入剧集代码')
    return
  }

  try {
    await $fetch(`${config.public.apiBase}/anime/${animeId.value}/episodes`, {
      method: 'POST',
      body: {
        episode_code: newEpisode.value.episode_code,
        episode_type: newEpisode.value.episode_type,
        display_order: newEpisode.value.display_order,
        title: newEpisode.value.title,
        air_date: newEpisode.value.air_date
      }
    })
    ElMessage.success('添加成功')
    showEpisodeDialog.value = false
    newEpisode.value = {
      episode_code: '',
      episode_type: 'main',
      display_order: 1,
      title: null,
      air_date: null
    }
    await loadEpData()
  } catch (error) {
    ElMessage.error('添加失败')
    console.error(error)
  }
}

const openEpisodeReview = async (episode: Episode) => {
  currentEpisodeCode.value = episode.episode_code
  try {
    const reviewData = await $fetch<EpisodeReview | null>(
      `${config.public.apiBase}/anime/${animeId.value}/episodes/${episode.episode_code}/review`
    )
    episodeReview.value = reviewData ? {
      score: reviewData.score ?? undefined,
      comment: reviewData.comment ?? undefined
    } : { score: undefined, comment: undefined }
    showReviewDialog.value = true
  } catch (error) {
    episodeReview.value = { score: undefined, comment: undefined }
    showReviewDialog.value = true
    console.error(error)
  }
}

const saveEpisodeReview = async () => {
  try {
    await $fetch(`${config.public.apiBase}/anime/${animeId.value}/episodes/${currentEpisodeCode.value}/review`, {
      method: 'POST',
      body: {
        score: episodeReview.value.score,
        comment: episodeReview.value.comment
      }
    })
    ElMessage.success('保存成功')

    // Update local state immediately
    const target = episodes.value.find(e => e.episode_code === currentEpisodeCode.value)
    if (target) {
      target.score = episodeReview.value.score
    }

    showReviewDialog.value = false
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  }
}

const saveAnimeReview = async () => {
  try {
    await $fetch(`${config.public.apiBase}/anime/${animeId.value}/review`, {
      method: 'POST',
      body: {
        score: animeReview.value.score,
        comment: animeReview.value.comment
      }
    })
    ElMessage.success('保存成功')
    await loadAnimeReview()
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  }
}

const deleteAnime = () => {
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
        await $fetch(`${config.public.apiBase}/anime/${animeId.value}`, {
          method: 'DELETE',
        })
        ElMessage.success('番剧已删除')
        router.push('/')
      } catch (error) {
        ElMessage.error('删除失败')
        console.error(error)
      }
    })
    .catch(() => {
      // 取消删除
    })
}

const deleteEpisode = (episode: Episode) => {
  ElMessageBox.confirm(
    `确定要删除剧集 ${episode.episode_code} 吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await $fetch(`${config.public.apiBase}/anime/${animeId.value}/episodes/${episode.episode_code}`, {
          method: 'DELETE',
        })
        ElMessage.success('剧集已删除')
        // Remove locally
        episodes.value = episodes.value.filter(e => e.episode_code !== episode.episode_code)
      } catch (error) {
        ElMessage.error('删除失败')
        console.error(error)
      }
    })
    .catch(() => {
      // 取消
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
