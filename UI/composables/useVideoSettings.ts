import { useStorage } from '@vueuse/core'


export interface VideoResultFormat {
  url: string;
  image: string;
  videoUrl?: {
    fileType: string;
    link: string;
    quality: string;
  };
  type?: "local" | "remote"
}

export interface VideoSegment {
  url: string;
  startTime: number;
  endTime: number;
}

export const useVideoSettings = () => {
  const video = useStorage<{
    script: string;
    voice: string;
    videoSubject: string;
    extraPrompt: string;
    search: string;
    aiModel: string;
    finalVideoUrl: string;
    selectedAudio: string;
    selectedVideoUrls: VideoResultFormat[];
    aspectRatio: string;
    subtitleTemplate: string;
    subtitlePosition: string;
    customSubtitle: string;
    videoSegments: VideoSegment[];
    backgroundMusicFromVideo: string;
    musicSource: "library" | "video";
  }>('VideoSettings', {
    script: "",
    voice: "",
    videoSubject: "",
    extraPrompt: "",
    search: "",

    aiModel: "g4f",

    finalVideoUrl: "",
    selectedAudio: "",
    selectedVideoUrls: [],
    aspectRatio: "9:16",
    subtitleTemplate: "classic",
    subtitlePosition: "bottom",
    customSubtitle: "",
    videoSegments: [],
    backgroundMusicFromVideo: "",
    musicSource: "library",
  });


  return { video }
}