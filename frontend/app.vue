<template>
  <div>
    <el-container>
      <el-header>
        <el-menu mode="horizontal" :default-active="activeIndex" @select="handleSelect">
          <el-menu-item index="home">
            <NuxtLink to="/">首页</NuxtLink>
          </el-menu-item>
          <el-menu-item index="collections">
            <NuxtLink to="/collections">收藏夹</NuxtLink>
          </el-menu-item>
        </el-menu>
      </el-header>
      <el-main>
        <NuxtPage />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const activeIndex = computed(() => {
  if (route.path === '/') return 'home'
  if (route.path.startsWith('/collections')) return 'collections'
  return 'home'
})

const handleSelect = (key: string) => {
  // 菜单选择由 NuxtLink 处理
}
</script>

<style>
a {
  text-decoration: none;
  color: inherit;
}
</style>
