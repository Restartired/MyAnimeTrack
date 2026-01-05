<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>番剧列表</span>
          <el-button type="primary" @click="showCreateDialog = true">添加番剧</el-button>
        </div>
      </template>
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

    <el-dialog v-model="showCreateDialog" title="添加番剧" width="500px">
      <el-form :model="newAnime" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="newAnime.title" placeholder="请输入番剧标题" />
        </el-form-item>
        <el-form-item label="开播日期">
          <el-date-picker
            v-model="newAnime.start_date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="总集数">
          <el-input-number v-model="newAnime.total_episodes" :min="1" />
        </el-form-item>
        <el-form-item label="来源ID">
          <el-input v-model="newAnime.source_id" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createAnime">确定</el-button>
      </template>
    </el-dialog>
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

const config = useRuntimeConfig()
const router = useRouter()

const { data: animeList, refresh } = await useFetch<Anime[]>(`${config.public.apiBase}/anime`, {
  default: () => [],
  server: false // 只在客户端执行，避免重复请求
})

const showCreateDialog = ref(false)
const newAnime = ref({
  title: '',
  start_date: null as string | null,
  total_episodes: null as number | null,
  source_id: null as string | null
})

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
    await refresh()
  } catch (error) {
    ElMessage.error('添加失败')
    console.error(error)
  }
}

const goToAnime = (id: number) => {
  router.push(`/anime/${id}`)
}
</script>
