<script lang="ts" setup>
import { useStorage } from "@vueuse/core";

interface VideoMetadata {
  title: string
  description: string
  tags: string[]
  post_content?: string
  suggested_schedule?: string
}

interface VideoItem {
  filename: string
  url: string
  metadata: VideoMetadata | null
}

interface MagicSyncAccount {
  platform: string
  accountName: string
  isActive: boolean
}

interface MagicSyncBusiness {
  id: string
  name: string
  url: string
  apiToken: string
  videoBaseUrl: string
}

const videos = ref<VideoItem[]>([])
const loading = ref(true)
const scheduleModal = ref(false)
const selectedVideo = ref<VideoItem | null>(null)
const scheduleDate = ref<number | null>(null)
const scheduleTime = ref<number | null>(null)
const scheduling = ref(false)
const scheduleResult = ref<string | null>(null)

const scheduleContent = ref('')
const scheduleTitle = ref('')
const scheduleDescription = ref('')

// MagicSync state
const magicsyncBusinesses = useStorage<MagicSyncBusiness[]>("MAGICSYNC_BUSINESSES", [])
const selectedBusinessId = ref<string | null>(null)
const magicsyncAccounts = ref<MagicSyncAccount[]>([])
const magicsyncLoading = ref(false)
const selectedPlatforms = ref<string[]>([])

const { API_SETTINGS } = useApiSettings()

const videoUrl = (filename: string) => {
  return `/api/video/${filename}`
}

const API_BASE = () => API_SETTINGS.value.URL.replace(/\/+$/, '')

const fetchVideos = async () => {
  try {
    const res = await $fetch<{ status: string; data: { videos: VideoItem[] } }>(
      `${API_BASE()}/api/getVideos`
    )
    if (res.status === 'success') {
      videos.value = res.data.videos
    }
  } catch (e) {
    console.error('Failed to fetch videos', e)
  } finally {
    loading.value = false
  }
}

const openScheduleModal = async (video: VideoItem) => {
  selectedVideo.value = video
  scheduleDate.value = null
  scheduleTime.value = null
  scheduleResult.value = null
  selectedPlatforms.value = []
  magicsyncAccounts.value = []
  scheduleContent.value = video.metadata?.post_content || video.metadata?.title || video.metadata?.description || video.filename
  scheduleTitle.value = video.metadata?.title || ''
  scheduleDescription.value = video.metadata?.description || ''
  if (video.metadata?.suggested_schedule) {
    const d = new Date(video.metadata.suggested_schedule)
    scheduleDate.value = d.getTime()
    scheduleTime.value = d.getTime()
  }

  // Auto-select first business if available
  if (magicsyncBusinesses.value.length > 0) {
    selectedBusinessId.value = magicsyncBusinesses.value[0].id
    await fetchAccountsForBusiness(selectedBusinessId.value)
  } else {
    selectedBusinessId.value = null
  }

  scheduleModal.value = true
}

async function fetchAccountsForBusiness(businessId: string | null) {
  if (!businessId) {
    magicsyncAccounts.value = []
    selectedPlatforms.value = []
    return
  }
  const biz = magicsyncBusinesses.value.find(b => b.id === businessId)
  if (!biz) return

  magicsyncLoading.value = true
  magicsyncAccounts.value = []
  selectedPlatforms.value = []
  try {
    const res = await $fetch<{ status: string; data: { accounts: MagicSyncAccount[] }; message?: string }>(
      `${API_BASE()}/api/magicsync/accounts`,
      { method: 'POST', body: { url: biz.url, apiToken: biz.apiToken } }
    )
    if (res.status === 'success') {
      magicsyncAccounts.value = res.data.accounts.filter(a => a.isActive)
      selectedPlatforms.value = [...new Set(magicsyncAccounts.value.map(a => a.platform))]
    }
  } catch (e) {
    console.error('Failed to fetch MagicSync accounts', e)
  } finally {
    magicsyncLoading.value = false
  }
}

const togglePlatform = (platform: string) => {
  const idx = selectedPlatforms.value.indexOf(platform)
  if (idx >= 0) {
    selectedPlatforms.value.splice(idx, 1)
  } else {
    selectedPlatforms.value.push(platform)
  }
}

const handleSchedule = async () => {
  if (!selectedVideo.value || !scheduleDate.value || !scheduleTime.value) return
  if (selectedPlatforms.value.length === 0) return
  if (!selectedBusinessId.value) return

  const biz = magicsyncBusinesses.value.find(b => b.id === selectedBusinessId.value)
  if (!biz) return

  scheduling.value = true
  scheduleResult.value = null

  try {
    const date = new Date(scheduleDate.value)
    const time = new Date(scheduleTime.value)
    date.setHours(time.getHours(), time.getMinutes(), 0, 0)
    const scheduledAt = date.toISOString()

    await $fetch(`${API_BASE()}/api/schedule-to-magicsync`, {
      method: 'POST',
      body: {
        videoFilename: selectedVideo.value.filename,
        scheduledAt,
        content: scheduleContent.value,
        title: scheduleTitle.value,
        description: scheduleDescription.value,
        platforms: selectedPlatforms.value,
        url: biz.url,
        apiToken: biz.apiToken,
        videoBaseUrl: biz.videoBaseUrl,
      }
    })

    scheduleResult.value = 'success'
    setTimeout(() => { scheduleModal.value = false }, 2000)
  } catch (e: any) {
    scheduleResult.value = `Error: ${e?.data?.message || e?.message || 'Unknown error'}`
  } finally {
    scheduling.value = false
  }
}

const deleteModal = ref(false)
const deleteTarget = ref<VideoItem | null>(null)
const deleting = ref(false)

const confirmDelete = async () => {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await $fetch(`${API_BASE()}/api/video/delete`, {
      method: 'POST',
      body: { filename: deleteTarget.value.filename }
    })
    videos.value = videos.value.filter(v => v.filename !== deleteTarget.value!.filename)
    deleteModal.value = false
    deleteTarget.value = null
  } catch (e: any) {
    console.error('Delete failed', e)
  } finally {
    deleting.value = false
  }
}

const openDeleteConfirm = (video: VideoItem) => {
  deleteTarget.value = video
  deleteModal.value = true
}

const applySuggestedSchedule = (video: VideoItem) => {
  if (!video.metadata?.suggested_schedule) return
  const date = new Date(video.metadata.suggested_schedule)
  scheduleDate.value = date.getTime()
  scheduleTime.value = date.getTime()
  if (video.metadata.post_content) {
    scheduleContent.value = video.metadata.post_content
  }
  openScheduleModal(video)
}

const uniquePlatforms = computed(() => {
  const seen = new Set<string>()
  for (const acc of magicsyncAccounts.value) {
    seen.add(acc.platform)
  }
  return [...seen]
})

onMounted(fetchVideos)
</script>

<template>
  <div class="py-28 px-10">
    <h1 class="text-3xl leading-10 font-bold mb-10">Generated Videos</h1>

    <div v-if="loading" class="flex justify-center items-center min-h-[200px]">
      <n-spin size="large" />
    </div>

    <div v-else-if="videos.length === 0" class="text-center py-10">
      <p class="text-gray-400">No generated videos yet.</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      <div v-for="video in videos" :key="video.filename" class="bg-slate-800 rounded-xl overflow-hidden flex flex-col">
        <div class="relative aspect-[9/16] bg-black">
          <video
            class="w-full h-full object-cover"
            :src="videoUrl(video.filename)"
            controls
            preload="metadata"
            crossorigin="anonymous"
          ></video>
        </div>

        <div class="p-4 flex-1 flex flex-col gap-2 min-w-0">
          <h3 class="font-semibold text-white truncate">
            {{ video.metadata?.title || video.filename }}
          </h3>
          <p v-if="video.metadata?.description" class="text-sm text-gray-400 line-clamp-2">
            {{ video.metadata.description }}
          </p>
          <div v-if="video.metadata?.tags?.length" class="flex flex-wrap gap-1">
            <span
              v-for="tag in video.metadata.tags"
              :key="tag"
              class="text-xs bg-slate-700 text-gray-300 px-2 py-0.5 rounded"
            >
              {{ tag }}
            </span>
          </div>
          <p v-if="video.metadata?.post_content" class="text-xs text-gray-500 line-clamp-2 italic">
            {{ video.metadata.post_content }}
          </p>
          <div v-if="video.metadata?.suggested_schedule" class="mt-1">
            <span
              class="text-xs text-blue-400 cursor-pointer hover:text-blue-300 underline decoration-dotted"
              @click="applySuggestedSchedule(video)"
            >
              <Icon name="mdi:calendar-clock" class="inline align-text-bottom" />
              Schedule: {{ new Date(video.metadata.suggested_schedule).toLocaleString() }}
            </span>
          </div>
        </div>

        <div class="px-4 pb-2 mt-auto flex gap-2">
          <n-button type="primary" size="small" class="flex-1" @click="openScheduleModal(video)">
            <template #icon>
              <Icon name="mdi:calendar-clock" />
            </template>
            Schedule
          </n-button>
          <n-button type="error" size="small" class="flex-shrink-0" @click="openDeleteConfirm(video)">
            <template #icon>
              <Icon name="mdi:delete" />
            </template>
          </n-button>
        </div>
      </div>
    </div>

    <n-modal
      v-model:show="deleteModal"
      preset="dialog"
      title="Delete Video"
      :content="`Are you sure you want to delete '${deleteTarget?.metadata?.title || deleteTarget?.filename}'?`"
      positive-text="Delete"
      negative-text="Cancel"
      :positive-button-props="{ type: 'error', loading: deleting }"
      @positive-click="confirmDelete"
      @negative-click="deleteModal = false"
    />

    <n-modal
      v-model:show="scheduleModal"
      preset="card"
      title="Schedule Upload"
      style="max-width: 520px"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <div v-if="selectedVideo">
          <p class="text-sm text-gray-400">
            Video:
            <span class="text-white">{{ selectedVideo.metadata?.title || selectedVideo.filename }}</span>
          </p>
        </div>

        <div v-if="magicsyncBusinesses.length > 0">
          <label class="block text-sm text-gray-400 mb-1">Business</label>
          <n-select
            v-model:value="selectedBusinessId"
            :options="magicsyncBusinesses.map(b => ({ label: b.name, value: b.id }))"
            class="w-full"
            @update:value="fetchAccountsForBusiness"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">Date</label>
          <n-date-picker v-model:value="scheduleDate" type="date" class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">Time</label>
          <n-time-picker v-model:value="scheduleTime" class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">Post Content</label>
          <n-input v-model:value="scheduleContent" type="textarea" :rows="3" placeholder="Post text..." class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">Title (optional)</label>
          <n-input v-model:value="scheduleTitle" placeholder="Video title" class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">Description (optional)</label>
          <n-input v-model:value="scheduleDescription" type="textarea" :rows="2" placeholder="Video description" class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">
            Post to
            <span v-if="magicsyncLoading" class="text-xs ml-1">(loading...)</span>
          </label>
          <div v-if="magicsyncLoading" class="flex items-center gap-2 text-sm text-gray-500">
            <n-spin size="small" />
            Fetching connected accounts...
          </div>
          <div v-else-if="magicsyncBusinesses.length === 0" class="text-sm text-yellow-400">
            No MagicSync businesses configured.
            <NuxtLink to="/settings" class="underline">Add one in Settings</NuxtLink>
          </div>
          <div v-else-if="uniquePlatforms.length === 0 && !magicsyncLoading" class="text-sm text-yellow-400">
            No connected accounts for this business.
          </div>
          <div v-else class="space-y-2">
            <div v-for="platform in uniquePlatforms" :key="platform" class="flex items-center gap-2">
              <n-checkbox
                :checked="selectedPlatforms.includes(platform)"
                @update:checked="togglePlatform(platform)"
              >
                <span class="text-sm capitalize">{{ platform }}</span>
              </n-checkbox>
            </div>
          </div>
        </div>

        <div v-if="scheduleResult === 'success'" class="text-green-400 text-sm font-medium">
          Scheduled successfully!
        </div>
        <div v-else-if="scheduleResult" class="text-red-400 text-sm">
          {{ scheduleResult }}
        </div>

        <div class="flex gap-3 pt-2">
          <n-button @click="scheduleModal = false" class="flex-1">Cancel</n-button>
          <n-button
            type="primary"
            class="flex-1"
            :loading="scheduling"
            :disabled="!scheduleDate || !scheduleTime || selectedPlatforms.length === 0"
            @click="handleSchedule"
          >
            Schedule
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>
