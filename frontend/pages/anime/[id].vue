<template>
  <div v-if="anime" v-loading="pending">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h2>{{ anime.title }}</h2>
          <div style="display: flex; gap: 10px;">
            <el-button type="primary" @click="showAddToCollectionDialog = true">加入收藏夹</el-button>
            <el-button type="danger" @click="deleteAnime">删除番剧</el-button>
          </div>
        </div>
      </template>
      <div style="margin-bottom: 20px">
        <div v-if="anime.start_date">开播日期: {{ anime.start_date }}</div>
        <div v-if="anime.total_episodes">总集数: {{ anime.total_episodes }}</div>
        <div v-if="anime.source_id">来源ID: {{ anime.source_id }}</div>
        <div v-if="anime.created_at" style="color: #666; font-size: 14px; margin-top: 5px;">
          上传时间: {{ formatDate(anime.created_at) }}
        </div>
      </div>
    </el-card>

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
          <div style="display: flex; gap: 20px; align-items: center;">
            <span>剧集列表</span>
            <el-select v-model="episodeSortBy" placeholder="排序" size="small" style="width: 120px;">
              <el-option label="默认(播放顺序)" value="default" />
              <el-option label="播出日期" value="air_date" />
              <el-option label="标题" value="title" />
            </el-select>
          </div>
          <el-button type="primary" @click="showEpisodeDialog = true">添加剧集</el-button>
        </div>
      </template>
      <el-table :data="sortedEpisodes || []" style="width: 100%" v-loading="episodesLoading">
        <el-table-column prop="episode_code" label="剧集代码" width="120" />
        <el-table-column prop="episode_type" label="类型" width="100" />
        <el-table-column prop="display_order" label="播放顺序" width="100" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="air_date" label="播出日期" width="120" />
        <el-table-column label="操作" width="180">
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
      <!-- (Episode Dialog Content) -->
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
          </el-select>
        </el-form-item>
        <el-form-item label="播放顺序" required>
          <el-input-number v-model="newEpisode.display_order" :min="1" />
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
}

interface Episode {
  episode_code: string
  episode_type: string
  display_order: number
  title: string | null
  air_date: string | null
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

const { data: anime, pending } = await useAsyncData<Anime>(
  `anime-${animeId.value}`,
  () => $fetch<Anime>(`${config.public.apiBase}/anime`).then(list => list.find(a => a.id === animeId.value) as Anime)
)

const episodes = ref<Episode[]>([])
const episodesLoading = ref(false)
const episodeSortBy = ref('default') // default (backend order), air_date, title

const sortedEpisodes = computed(() => {
  if (!episodes.value) return []
  const list = [...episodes.value]

  switch (episodeSortBy.value) {
    case 'default':
      // Backend order (now air_date, display_order)
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

const loadData = async () => {
  if (!animeId.value) return

  episodesLoading.value = true
  try {
    const [episodesData, reviewData] = await Promise.all([
      $fetch<Episode[]>(`${config.public.apiBase}/anime/${animeId.value}/episodes`),
      $fetch<AnimeReview | null>(`${config.public.apiBase}/anime/${animeId.value}/review`).catch(() => null)
    ])

    episodes.value = episodesData || []

    animeReview.value = reviewData ? {
      score: reviewData.score ?? undefined,
      comment: reviewData.comment ?? undefined
    } : { score: undefined, comment: undefined }

  } catch (e) {
    console.error(e)
  } finally {
    episodesLoading.value = false
  }
}

await loadData()

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
    await loadData()
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
    await loadData()
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
        await loadData()
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
