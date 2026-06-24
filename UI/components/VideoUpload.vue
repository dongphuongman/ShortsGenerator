<script setup>
const { video } = useVideoSettings()
const URL = useApiSettings().API_SETTINGS.value.URL;
const fileInput = ref(null)
const selectedFiles = ref([])
const isUploading = ref(false)
const uploadStatus = ref([])
const handleFileSelect = (event) => {
  const input = event.target
  if (input.files) {
    selectedFiles.value = Array.from(input.files)
  }
}

const uploadFiles = async () => {
  if (selectedFiles.value.length === 0) return
  isUploading.value = true
  uploadStatus.value = []

  try {
    const formData = new FormData()
    for (const file of selectedFiles.value) {
      formData.append('file', file)
    }

    const response = await fetch(`${URL}/api/upload-video`, {
      method: 'POST',
      body: formData,
    })

    const data = await response.json()

    if (data.status === 'success') {
      for (const filename of data.data.filenames) {
        if (!video.value.selectedVideoUrls) {
          video.value.selectedVideoUrls = []
        }
        video.value.selectedVideoUrls.push({
          url: `static/generated_videos/instagram/${filename}`,
          image: `${URL}/static/generated_videos/instagram/${filename}`,
          videoUrl: { fileType: 'mp4', link: `${URL}/static/generated_videos/instagram/${filename}`, quality: 'hd' },
          type: 'local'
        })
      }
      uploadStatus.value.push({
        type: 'success',
        message: `Uploaded ${data.data.filenames.length} video(s) and added to selection`,
      })
      selectedFiles.value = []
    } else {
      throw new Error(data.message || 'Upload failed')
    }
  } catch (error) {
    uploadStatus.value.push({
      type: 'error',
      message: `Upload failed: ${error.message}`,
    })
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">Upload Videos</h1>

    <div class="bg-white rounded-lg shadow p-6">
      <div class="space-y-4">
        <div
          class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors"
          @click="fileInput?.click()"
        >
          <Icon name="mdi:cloud-upload" size="48" class="text-gray-400 mb-2" />
          <p class="text-gray-600">Click to select videos or drag them here</p>
          <p class="text-sm text-gray-400 mt-1">MP4, MOV, AVI, MKV, WebM</p>
          <input
            ref="fileInput"
            type="file"
            multiple
            accept=".mp4,.mov,.avi,.mkv,.webm,.flv,.wmv"
            class="hidden"
            @change="handleFileSelect"
          />
        </div>

        <div v-if="selectedFiles.length > 0" class="mt-4">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">Selected files ({{ selectedFiles.length }}):</h3>
          <ul class="space-y-1">
            <li v-for="(file, idx) in selectedFiles" :key="idx" class="text-sm text-gray-600 flex items-center gap-2">
              <Icon name="mdi:file-video" class="text-blue-500" />
              {{ file.name }} ({{ (file.size / 1024 / 1024).toFixed(1) }} MB)
            </li>
          </ul>
        </div>

        <div class="flex justify-end mt-6">
          <button
            @click="uploadFiles"
            :disabled="selectedFiles.length === 0 || isUploading"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="isUploading">Uploading...</span>
            <span v-else>Upload Videos</span>
          </button>
        </div>
      </div>

      <div class="mt-6 space-y-2">
        <div
          v-for="(status, index) in uploadStatus"
          :key="index"
          :class="[
            'p-4 rounded-lg',
            status.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          ]"
        >
          {{ status.message }}
        </div>
      </div>
    </div>
  </div>
</template>
