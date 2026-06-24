<script lang="ts" setup>
/**
 *
 * GenerateScript
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

interface Props {
  activeTab: "ALL" | "VOICE" | "SUBTITLE" | "MUSIC";
}
const props = withDefaults(defineProps<Props>(), {
  activeTab: "ALL",
});
const currentTab = ref(props.activeTab);
</script>

<template>
  <div class="mt-20">
    <n-tabs
      type="line"
      animated
      v-model:value="currentTab"
      display-directive="if"
    >
      <n-tab-pane name="ALL" tab="All">
        <AllSettings />
      </n-tab-pane>
      <n-tab-pane name="VOICE" tab="Voice">
        <VoiceSettings />
      </n-tab-pane>
      <n-tab-pane name="MUSIC" tab="Audio">
        <MusicSettings />
      </n-tab-pane>
      <n-tab-pane name="SUBTITLE" tab="Subtitle">
        <SubtitleSettings />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>
<style scoped></style>
