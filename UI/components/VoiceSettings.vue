<script lang="ts" setup>
/**
 *
 * Component Description:Desc
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

const { API_SETTINGS } = useApiSettings();
const voiceOptions = ref<{ label: string; value: string; description?: string }[]>([]);
const voiceStyles = ref<Record<string, { name: string; description: string; gender: string }>>({});
const selectedVoice = ref("M3");

const { video } = useVideoSettings();

onMounted(async () => {
  try {
    const res = await $fetch<{ data: { voices: string[]; voiceStyles?: Record<string, { name: string; description: string; gender: string }> } }>(
      `${API_SETTINGS.value.URL}/api/models`
    );
    const data = res.data;
    if (data && data.voiceStyles) {
      voiceStyles.value = data.voiceStyles;
      voiceOptions.value = data.voices.map((v) => ({
        label: `${v} - ${data.voiceStyles?.[v]?.name || v} (${data.voiceStyles?.[v]?.gender || ""})`,
        value: v,
        description: data.voiceStyles?.[v]?.description,
      }));
    } else if (data) {
      voiceOptions.value = data.voices.map((v) => ({ label: v, value: v }));
    }
  } catch {
    voiceOptions.value = [{ label: "Default", value: "M3" }];
  }
});

watch(video, () => {
  if (video.value?.voice) {
    selectedVoice.value = video.value.voice;
  }
  video.value.voice = selectedVoice.value;
}, { immediate: true, deep: true });
</script>

<template>
  <n-form-item label="Voice:" path="voice">
    <n-select v-model:value="video.voice" :options="voiceOptions" />
  </n-form-item>
</template>
<style scoped></style>
