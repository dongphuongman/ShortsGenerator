<script lang="ts" setup>
interface ScriptSettings {
  defaultPromptEnd: string;
  defaultPromptStart: string;
}
interface FontSettings {
  font: string;
  fontsize: number;
  color: string;
  stroke_color: string;
  stroke_width: number;
  subtitles_position:
    | "center,top"
    | "center,bottom"
    | "center,center"
    | "left,center"
    | "left,bottom"
    | "right,center"
    | "right,bottom";
}
interface VoiceStyle {
  name: string;
  description: string;
  gender: string;
}
interface LanguageOption {
  code: string;
  label: string;
}
interface QualityPreset {
  value: number;
  label: string;
}
interface AspectRatioOption {
  value: string;
  label: string;
  width: number;
  height: number;
}
interface AspectRatioSettings {
  current: string;
  options: AspectRatioOption[];
}
interface TitleColorOption {
  value: string;
  label: string;
  sample: string;
}
interface TitleColorSettings {
  current: string;
  options: TitleColorOption[];
}
interface FontOption {
  value: string;
  label: string;
}
interface FontOptions {
  current: string;
  options: FontOption[];
}
interface SubtitleTemplateOption {
  value: string;
  label: string;
  description: string;
  color: string;
  stroke_color: string;
  stroke_width: number;
  fontsize: number;
  position: string;
}
interface SubtitleTemplates {
  current: string;
  options: SubtitleTemplateOption[];
}
interface GlobalSettings {
  fontSettings: FontSettings;
  scriptSettings: ScriptSettings;
  ttsSettings: TTSSettings;
  aspectRatioSettings: AspectRatioSettings;
  titleColorSettings: TitleColorSettings;
  fontOptions: FontOptions;
  subtitleTemplates: SubtitleTemplates;
}
interface TTSSettings {
  preferred_tts: "supertonic" | "tiktok";
  tts_voice: string;
  tts_lang: string;
  tts_quality: number;
  tts_speed: number;
}

import { useStorage } from "@vueuse/core";

const isLoading = ref(false);
const API_URL = "http://localhost:8080";

// MagicSync config
const magicsyncUrl = useStorage("MAGICSYNC_URL", "http://localhost:3000")
const magicsyncApiToken = useStorage("MAGICSYNC_API_TOKEN", "")
const videoBaseUrl = useStorage("VIDEO_BASE_URL", "http://localhost:8080")
const magicsyncAccounts = ref<{ accountId: string; accountName: string; platform: string; isActive: boolean }[]>([])
const magicsyncTesting = ref(false)
const magicsyncError = ref("")
const magicsyncConnected = ref(false)

async function testMagicsyncConnection() {
  magicsyncTesting.value = true
  magicsyncError.value = ""
  magicsyncAccounts.value = []
  magicsyncConnected.value = false
  try {
    const res = await $fetch<{ status: string; data: { accounts: any[] }; message?: string }>(
      `${API_URL}/api/magicsync/accounts`,
      {
        method: "POST",
        body: { url: magicsyncUrl.value, apiToken: magicsyncApiToken.value }
      }
    )
    if (res.status === "success") {
      magicsyncAccounts.value = res.data.accounts
      magicsyncConnected.value = true
    } else {
      magicsyncError.value = res.message || "Connection failed"
    }
  } catch (e: any) {
    magicsyncError.value = e?.data?.message || e?.message || "Connection failed"
  } finally {
    magicsyncTesting.value = false
  }
}

const voiceOptions = ref<{ label: string; value: string; description?: string }[]>([]);
const voicesLoading = ref(false);
const voiceStyles = ref<Record<string, VoiceStyle>>({});
const languageOptions = ref<LanguageOption[]>([]);
const qualityPresets = ref<QualityPreset[]>([]);

const { globalSettings } = useGlobalSettings();

const ttsEngineOptions = [
  { label: "Supertonic TTS (Local)", value: "supertonic" },
  { label: "TikTok TTS (Cloud)", value: "tiktok" },
];

const ttsStatus = ref<{ supertonic: string; tiktok: string }>({
  supertonic: "unavailable",
  tiktok: "available",
});

const aiModelOptions = [
  { label: "FREE", value: "g4f" },
  { label: "GPT 4", value: "gpt4" },
  { label: "GPT 3.5 Turbo", value: "gpt3.5-turbo" },
];

const settingsRule = {
  font: { required: true, trigger: ["input", "blur"] },
  fontColor: { required: true, trigger: ["input", "blur"] },
  subtitlePosition: { required: true, trigger: ["input", "blur"] },
  aiModel: { required: true, trigger: ["change", "blur"] },
};

const subtitlePositionOptions = [
  "center,top", "center,bottom", "center,center",
  "left,center", "left,bottom", "right,center", "right,bottom",
];

const selectedVoice = ref("");
const selectedLang = ref("en");
const selectedQuality = ref(8);
const selectedSpeed = ref(1.05);

async function loadVoices(engine: string) {
  voicesLoading.value = true;
  try {
    const res = await $fetch<{
      data: {
        voices: string[];
        voiceStyles?: Record<string, VoiceStyle>;
        languages?: LanguageOption[];
        qualityPresets?: QualityPreset[];
      };
    }>(`${API_URL}/api/tts/voices?engine=${engine}`);
    const data = res.data;
    if (data.voiceStyles) {
      voiceStyles.value = data.voiceStyles;
      voiceOptions.value = data.voices.map((v) => ({
        label: `${v} - ${data.voiceStyles?.[v]?.name || v} (${data.voiceStyles?.[v]?.gender || ""})`,
        value: v,
        description: data.voiceStyles?.[v]?.description,
      }));
    } else {
      voiceOptions.value = data.voices.map((v) => ({ label: v, value: v }));
    }
    if (data.languages) languageOptions.value = data.languages;
    if (data.qualityPresets) qualityPresets.value = data.qualityPresets;
  } catch (error) {
    console.error("Failed to load voices:", error);
  } finally {
    voicesLoading.value = false;
  }
}

async function loadTtsStatus() {
  try {
    const { data } = await $fetch<{
      data: { supertonic: string; tiktok: string };
    }>(`${API_URL}/api/tts/status`);
    ttsStatus.value = data;
  } catch (error) {
    console.error("Failed to load TTS status:", error);
  }
}

const { data: mainSettings } = await $fetch<{
  data: GlobalSettings;
}>(`${API_URL}/api/settings`);

globalSettings.value.font = mainSettings.fontSettings.font;
globalSettings.value.color = mainSettings.fontSettings.color;
globalSettings.value.fontsize = mainSettings.fontSettings.fontsize;
globalSettings.value.stroke_color = mainSettings.fontSettings.stroke_color;
globalSettings.value.stroke_width = mainSettings.fontSettings.stroke_width;
globalSettings.value.subtitles_position = mainSettings.fontSettings.subtitles_position;

const ttsEngine = ref(mainSettings.ttsSettings?.preferred_tts || "supertonic");
selectedVoice.value = mainSettings.ttsSettings?.tts_voice || "M3";
selectedLang.value = mainSettings.ttsSettings?.tts_lang || "en";
selectedQuality.value = mainSettings.ttsSettings?.tts_quality || 8;
selectedSpeed.value = mainSettings.ttsSettings?.tts_speed || 1.05;

const aspectRatio = ref(mainSettings.aspectRatioSettings?.current || "9:16");
const aspectRatioOptions = ref(mainSettings.aspectRatioSettings?.options || []);
const titleColor = ref(mainSettings.titleColorSettings?.current || "#FFFF00");
const titleColorOptions = ref(mainSettings.titleColorSettings?.options || []);
const selectedFont = ref(mainSettings.fontOptions?.current || "bold_font.ttf");
const fontOptionsList = ref(mainSettings.fontOptions?.options || []);
const subtitleTemplate = ref(mainSettings.subtitleTemplates?.current || "classic");
const subtitleTemplateOptions = ref(mainSettings.subtitleTemplates?.options || []);

await loadVoices(ttsEngine.value);
await loadTtsStatus();

async function onTtsEngineChange(engine: string) {
  await loadVoices(engine);
  await saveTtsSettings();
}

async function saveTtsSettings() {
  const settings: Record<string, unknown> = {
    preferred_tts: ttsEngine.value,
  };
  if (ttsEngine.value === "supertonic") {
    settings.tts_voice = selectedVoice.value;
    settings.tts_lang = selectedLang.value;
    settings.tts_quality = selectedQuality.value;
    settings.tts_speed = selectedSpeed.value;
  }
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "TTS", settings },
    });
  } catch (error) {
    console.error("Failed to save TTS settings:", error);
  }
}

async function saveAspectRatio() {
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "ASPECT", settings: { current: aspectRatio.value } },
    });
  } catch (error) {
    console.error("Failed to save aspect ratio:", error);
  }
}

async function saveFontSettings() {
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "FONT", settings: { font: `static/assets/fonts/${selectedFont.value}` } },
    });
  } catch (error) {
    console.error("Failed to save font settings:", error);
  }
}

async function saveTitleColor() {
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "FONT", settings: { color: titleColor.value } },
    });
  } catch (error) {
    console.error("Failed to save title color:", error);
  }
}

async function saveSubtitleTemplate() {
  const template = subtitleTemplateOptions.value.find(t => t.value === subtitleTemplate.value);
  if (!template) return;
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: {
        type: "FONT",
        settings: {
          color: template.color, stroke_color: template.stroke_color,
          stroke_width: template.stroke_width, fontsize: template.fontsize,
          subtitles_position: template.position,
        },
      },
    });
  } catch (error) {
    console.error("Failed to save subtitle template:", error);
  }
}

const HandleSaveSettings = async () => {};
</script>

<template>
  <div class="min-h-screen flex flex-col justify-center items-center p-4">
    <header class="text-3xl leading-10 font-bold">Global Settings</header>

    <n-form
      ref="formRef"
      class="max-w-screen-md mt-10 w-full"
      :model="globalSettings"
      :rules="settingsRule"
      size="large"
      :disabled="isLoading"
    >
      <n-form-item label="AI Model:" path="aiModel">
        <n-select v-model:value="globalSettings.aiModel" :options="aiModelOptions" class="w-full md:w-auto" />
      </n-form-item>

      <n-divider>TTS Settings</n-divider>

      <div class="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg mb-4">
        <n-form-item label="TTS Engine:" path="ttsEngine">
          <div class="flex items-center gap-3 w-full">
            <n-select v-model:value="ttsEngine" :options="ttsEngineOptions" class="flex-1" @update:value="onTtsEngineChange" />
            <n-tag :type="ttsStatus.supertonic === 'healthy' ? 'success' : 'warning'" size="small">
              {{ ttsStatus.supertonic === 'healthy' ? "Supertonic OK" : "Supertonic Down" }}
            </n-tag>
          </div>
        </n-form-item>

        <template v-if="ttsEngine === 'supertonic'">
          <n-form-item label="Voice Style:" path="supertonicVoice">
            <n-select
              v-model:value="selectedVoice"
              :options="voiceOptions"
              :loading="voicesLoading"
              class="w-full"
              @update:value="saveTtsSettings"
            />
          </n-form-item>

          <div v-if="selectedVoice && voiceStyles[selectedVoice]" class="text-xs text-gray-500 dark:text-gray-400 -mt-3 mb-3 px-1">
            {{ voiceStyles[selectedVoice]?.description }}
          </div>

          <n-form-item label="Language:" path="supertonicLang">
            <n-select
              v-model:value="selectedLang"
              :options="languageOptions.map(l => ({ label: l.label, value: l.code }))"
              class="w-full"
              @update:value="saveTtsSettings"
            />
          </n-form-item>

          <n-form-item label="Quality:" path="supertonicQuality">
            <n-slider
              v-model:value="selectedQuality"
              :min="5"
              :max="12"
              :step="1"
              :marks="{
                5: 'Fast',
                8: 'Standard',
                12: 'Best'
              }"
              class="w-full"
              @update:value="saveTtsSettings"
            />
            <div class="text-xs text-gray-500 mt-1">
              {{ qualityPresets.find(q => q.value === selectedQuality)?.label || `${selectedQuality} steps` }}
            </div>
          </n-form-item>

          <n-form-item label="Speed:" path="supertonicSpeed">
            <n-slider
              v-model:value="selectedSpeed"
              :min="0.7"
              :max="2.0"
              :step="0.05"
              :marks="{
                0.7: 'Slow',
                1.0: 'Normal',
                1.5: 'Fast',
                2.0: 'Max'
              }"
              class="w-full"
              @update:value="saveTtsSettings"
            />
            <div class="text-xs text-gray-500 mt-1">
              {{ selectedSpeed.toFixed(2) }}x speed
            </div>
          </n-form-item>
        </template>

        <template v-else>
          <n-form-item label="Voice:" path="voice">
            <n-select
              v-model:value="globalSettings.voice"
              :options="voiceOptions"
              :loading="voicesLoading"
              class="w-full md:w-auto"
            />
          </n-form-item>
        </template>
      </div>

      <n-divider />

      <n-form-item label="Font:" path="font">
        <n-input v-model:value="globalSettings.font" placeholder="Font for the subtitle" show-count clearable class="w-full" />
      </n-form-item>
      <n-form-item label="Color(#18A058)" path="fontcolor">
        <n-color-picker v-model:value="globalSettings.color" :show-alpha="false" class="w-full md:w-auto" />
      </n-form-item>
      <n-form-item label="Subtitle position:" path="subtitlePosition">
        <n-radio-group v-model:value="globalSettings.subtitles_position" name="subtitlePosition" size="medium" class="flex flex-wrap gap-2">
          <n-radio-button v-for="position in subtitlePositionOptions" :key="position" :value="position">
            <span class="capitalize">{{ position }}</span>
          </n-radio-button>
        </n-radio-group>
      </n-form-item>
      <n-form-item label="Font size:">
        <n-input-number v-model:value="globalSettings.fontsize" placeholder="Font for the subtitle" class="w-full" />
      </n-form-item>

      <n-form-item label="Stroke color(#18A058)">
        <n-color-picker v-model:value="globalSettings.stroke_color" class="w-full md:w-auto" />
      </n-form-item>
      <n-form-item label="Stroke width:">
        <n-input-number v-model:value="globalSettings.stroke_width" placeholder="Font for the subtitle" class="w-full" />
      </n-form-item>

      <n-divider>Video Settings</n-divider>

      <div class="bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg mb-4">
        <n-form-item label="Aspect Ratio:">
          <n-select v-model:value="aspectRatio" :options="aspectRatioOptions.map(o => ({ label: o.label, value: o.value }))" class="w-full" @update:value="saveAspectRatio" />
        </n-form-item>
      </div>

      <n-divider>Subtitle Templates</n-divider>

      <div class="bg-purple-50 dark:bg-purple-900/30 p-4 rounded-lg mb-4">
        <n-form-item label="Template:">
          <n-select v-model:value="subtitleTemplate" :options="subtitleTemplateOptions.map(t => ({ label: t.label, value: t.value, description: t.description }))" class="w-full" @update:value="saveSubtitleTemplate" />
        </n-form-item>
        <div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {{ subtitleTemplateOptions.find(t => t.value === subtitleTemplate)?.description }}
        </div>
      </div>

      <n-divider>Title Color & Font</n-divider>

      <div class="bg-green-50 dark:bg-green-900/30 p-4 rounded-lg mb-4">
        <n-form-item label="Title Color:">
          <div class="flex flex-wrap gap-2">
            <n-button
              v-for="color in titleColorOptions" :key="color.value" size="small"
              :type="titleColor === color.value ? 'primary' : 'default'"
              :style="{ backgroundColor: color.value, borderColor: titleColor === color.value ? '#fff' : color.value }"
              @click="titleColor = color.value; saveTitleColor()"
            >
              <span :style="{ color: color.value === '#000000' ? '#fff' : color.value }">★</span>
            </n-button>
          </div>
        </n-form-item>

        <n-form-item label="Font:">
          <n-select v-model:value="selectedFont" :options="fontOptionsList.map(f => ({ label: f.label, value: f.value }))" class="w-full" @update:value="saveFontSettings" />
        </n-form-item>
      </div>

      <n-divider>MagicSync Integration</n-divider>

      <div class="bg-emerald-50 dark:bg-emerald-900/30 p-4 rounded-lg mb-4">
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Connect to MagicSync to schedule video uploads to social media platforms.
        </p>
        <n-form-item label="MagicSync URL:">
          <n-input v-model:value="magicsyncUrl" placeholder="http://localhost:3000" class="w-full" />
        </n-form-item>
        <n-form-item label="API Token:">
          <n-input
            v-model:value="magicsyncApiToken"
            type="password"
            show-password-on="click"
            placeholder="Enter your MagicSync API token"
            class="w-full"
          />
        </n-form-item>
        <n-form-item label="Video Asset Base URL:">
          <n-input v-model:value="videoBaseUrl" placeholder="http://localhost:8080" class="w-full" />
          <template #feedback>
            Base URL for video assets served by the Python backend
          </template>
        </n-form-item>
        <div class="flex items-start gap-4 flex-wrap">
          <n-button
            type="primary"
            :loading="magicsyncTesting"
            :disabled="!magicsyncUrl || !magicsyncApiToken"
            @click="testMagicsyncConnection"
          >
            <template #icon>
              <Icon name="mdi:connection" />
            </template>
            Test Connection
          </n-button>

          <div v-if="magicsyncConnected" class="flex-1 min-w-0">
            <div class="text-sm text-green-400 font-medium mb-2">✓ Connected — {{ magicsyncAccounts.length }} account(s)</div>
            <div v-if="magicsyncAccounts.length > 0" class="space-y-1">
              <div v-for="acc in magicsyncAccounts" :key="acc.accountId" class="text-xs text-gray-400 flex items-center gap-2">
                <Icon name="mdi:check-circle" class="text-green-400" />
                <span>{{ acc.platform }} — {{ acc.accountName }}</span>
                <n-tag v-if="!acc.isActive" size="tiny" type="warning">inactive</n-tag>
              </div>
            </div>
          </div>
          <div v-else-if="magicsyncError" class="text-sm text-red-400">
            {{ magicsyncError }}
          </div>
        </div>
      </div>

      <n-form-item>
        <n-button @click="HandleSaveSettings" type="success" ghost :loading="isLoading" :disabled="isLoading">
          Save settings
        </n-button>
      </n-form-item>
    </n-form>
  </div>
</template>
<style scoped></style>