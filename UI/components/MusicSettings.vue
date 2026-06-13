<script lang="ts" setup>
const { API_SETTINGS } = useApiSettings();
const availableSongs = ref<string[]>([]);
const { video } = useVideoSettings();

const uploadLoading = ref(false)
const uploadResult = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const downloadUrl = ref('')
const downloadLoading = ref(false)
const downloadResult = ref<string | null>(null)

const API_BASE = API_SETTINGS.value.URL

async function loadSongs() {
  const { data: songsResponse } = await $fetch<{ data: { songs: string[] } }>(
    `${API_BASE}/api/getSongs`
  );
  availableSongs.value = songsResponse.songs;
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  uploadLoading.value = true
  uploadResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', input.files[0])
    await $fetch(`${API_BASE}/api/upload-music`, {
      method: 'POST',
      body: formData,
    })
    uploadResult.value = 'Uploaded successfully!'
    input.value = ''
    await loadSongs()
  } catch (e: any) {
    uploadResult.value = e?.data?.message || e?.message || 'Upload failed'
  } finally {
    uploadLoading.value = false
  }
}

async function handleDownloadUrl() {
  if (!downloadUrl.value.trim()) return
  downloadLoading.value = true
  downloadResult.value = null
  try {
    await $fetch(`${API_BASE}/api/download-music-url`, {
      method: 'POST',
      body: { url: downloadUrl.value.trim() },
    })
    downloadResult.value = 'Downloaded successfully!'
    downloadUrl.value = ''
    await loadSongs()
  } catch (e: any) {
    downloadResult.value = e?.data?.message || e?.message || 'Download failed'
  } finally {
    downloadLoading.value = false
  }
}

onMounted(loadSongs)
</script>

<template>
  <n-form ref="reviewFormRef" class="max-w-screen-md" :model="video" size="large">
    <n-form-item label="Select audio:" path="voice">
      <n-radio-group v-model:value="video.selectedAudio" name="radiogroup">
        <n-space :vertical="true">
          <n-radio
            v-for="song in availableSongs"
            :key="song"
            :value="song"
            :label="song"
          />
        </n-space>
      </n-radio-group>
    </n-form-item>
    <div>
      <audio controls v-for="song in availableSongs" :key="song" class="mb-5">
        <source :src="`${API_BASE}/static/assets/music/${song}`" type="audio/mp4" />
      </audio>
    </div>

    <n-divider>Upload Audio File</n-divider>
    <div class="space-y-3">
      <input ref="fileInput" type="file" accept=".mp3,.wav,.m4a,.aac,.ogg,.flac" class="hidden" @change="handleUpload" />
      <n-button :loading="uploadLoading" type="info" ghost @click="triggerUpload">
        <template #icon><Icon name="mdi:upload" /></template>
        Upload Audio
      </n-button>
      <p v-if="uploadResult" :class="uploadResult === 'Uploaded successfully!' ? 'text-green-400 text-sm' : 'text-red-400 text-sm'">
        {{ uploadResult }}
      </p>
    </div>

    <n-divider>Download from URL</n-divider>
    <div class="space-y-3">
      <div class="flex gap-2">
        <n-input v-model:value="downloadUrl" placeholder="YouTube, SoundCloud, etc. URL" class="flex-1" />
        <n-button :loading="downloadLoading" :disabled="!downloadUrl.trim()" type="info" ghost @click="handleDownloadUrl">
          <template #icon><Icon name="mdi:download" /></template>
          Download
        </n-button>
      </div>
      <p v-if="downloadResult" :class="downloadResult === 'Downloaded successfully!' ? 'text-green-400 text-sm' : 'text-red-400 text-sm'">
        {{ downloadResult }}
      </p>
    </div>
  </n-form>
</template>
<style scoped></style>
