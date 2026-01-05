<template>
  <div v-if="anime">
    <el-card>
      <template #header>
        <h2>{{ anime.title }}</h2>
      </template>
      <div style="margin-bottom: 20px">
        <div v-if="anime.start_date">开播日期: {{ anime.start_date }}</div>
        <div v-if="anime.total_episodes">总集数: {{ anime.total_episodes }}</div>
        <div v-if="anime.source_id">来源ID: {{ anime.source_id }}</div>
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
          <el-input
            v-model="animeReview.comment"
            type="textarea"
            :rows="4"
            placeholder="请输入评价"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveAnimeReview">保存评价</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>剧集列表</span>
          <el-button type="primary" @click="showEpisodeDialog = true">添加剧集</el-button>
        </div>
      </template>
      <el-table :data="episodes || []" style="width: 100%" v-loading="episodesLoading">
        <el-table-column prop="episode_code" label="剧集代码" width="120" />
        <el-table-column prop="episode_type" label="类型" width="100" />
        <el-table-column prop="display_order" label="播放顺序" width="100" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="air_date" label="播出日期" width="120" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="openEpisodeReview(row)">评价</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="episodes && episodes.length === 0" description="暂无剧集" />
    </el-card>

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
          </el-select>
        </el-form-item>
        <el-form-item label="播放顺序" required>
          <el-input-number v-model="newEpisode.display_order" :min="1" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="newEpisode.title" placeholder="可选" />
        </el-form-item>
        <el-form-item label="播出日期">
          <el-date-picker
            v-model="newEpisode.air_date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
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
          <el-input
            v-model="episodeReview.comment"
            type="textarea"
            :rows="4"
            placeholder="请输入评价"
          />
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
import { ElMessage } from 'element-plus'

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

const route = useRoute()
const config = useRuntimeConfig()
const animeId = parseInt(route.params.id as string)

// 由于后端没有 GET /anime/{id}，我们需要从列表中找到对应的番剧
const { data: animeList } = await useFetch<Anime[]>(`${config.public.apiBase}/anime`, {
  default: () => [],
  server: false // 只在客户端执行，避免重复请求
})
const anime = computed(() => {
  return animeList.value?.find(a => a.id === animeId)
})

const { data: episodes, refresh: refreshEpisodes, pending: episodesLoading } = await useFetch<Episode[]>(
  `${config.public.apiBase}/anime/${animeId}/episodes`,
  {
    default: () => [],
    server: false // 只在客户端执行，避免重复请求
  }
)

const { data: animeReviewData, refresh: refreshAnimeReview } = await useFetch<AnimeReview | null>(
  `${config.public.apiBase}/anime/${animeId}/review`,
  {
    default: () => null,
    server: false // 只在客户端执行，避免重复请求
  }
)

const animeReview = ref<AnimeReview>({
  score: undefined,
  comment: undefined
})

watch(animeReviewData, (data) => {
  if (data) {
    animeReview.value = {
      score: data.score ?? undefined,
      comment: data.comment ?? undefined
    }
  } else {
    animeReview.value = {
      score: undefined,
      comment: undefined
    }
  }
}, { immediate: true })

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
    await $fetch(`${config.public.apiBase}/anime/${animeId}/episodes`, {
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
    await refreshEpisodes()
  } catch (error) {
    ElMessage.error('添加失败')
    console.error(error)
  }
}

const openEpisodeReview = async (episode: Episode) => {
  currentEpisodeCode.value = episode.episode_code
  try {
    const reviewData = await $fetch<EpisodeReview | null>(
      `${config.public.apiBase}/anime/${animeId}/episodes/${episode.episode_code}/review`
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
    await $fetch(`${config.public.apiBase}/anime/${animeId}/episodes/${currentEpisodeCode.value}/review`, {
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
    await $fetch(`${config.public.apiBase}/anime/${animeId}/review`, {
      method: 'POST',
      body: {
        score: animeReview.value.score,
        comment: animeReview.value.comment
      }
    })
    ElMessage.success('保存成功')
    await refreshAnimeReview()
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  }
}
</script>
